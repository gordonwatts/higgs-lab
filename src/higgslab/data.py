"""dataset-v1 generation and validation. Default samples are synthetic, not ATLAS."""
import hashlib
import json
from pathlib import Path
import numpy as np

FLOAT_COLUMNS = [f"{kind}_{x}_{i}" for kind in ("lep", "jet") for i in range(2) for x in ("pt", "eta", "phi")] + ["met_et", "met_phi"]
INT_COLUMNS = ["lep_charge_0", "lep_charge_1", "lep_type_0", "lep_type_1", "jet_n"]
COLUMNS = FLOAT_COLUMNS + INT_COLUMNS

def _events(rng, n, signal):
    e = {}
    for i in range(2):
        e[f"lep_pt_{i}"] = rng.gamma(4, 10 if signal else 13, n) + 10
        e[f"lep_eta_{i}"] = rng.normal(0, 0.85 if signal else 1.1, n)
    e["lep_phi_0"] = rng.uniform(-np.pi, np.pi, n)
    delta = rng.normal(0, .7, n) if signal else rng.uniform(-np.pi, np.pi, n)
    e["lep_phi_1"] = np.arctan2(np.sin(e["lep_phi_0"]+delta), np.cos(e["lep_phi_0"]+delta))
    e["met_et"] = rng.gamma(3, 15 if signal else 11, n)
    e["met_phi"] = rng.uniform(-np.pi, np.pi, n)
    e["jet_n"] = rng.choice(3, n, p=[.55,.3,.15])
    for i in range(2):
        present = e["jet_n"] > i
        e[f"jet_pt_{i}"] = np.where(present, rng.gamma(3, 15, n)+20, 0)
        e[f"jet_eta_{i}"] = np.where(present, rng.normal(0, 1.8, n), 0)
        e[f"jet_phi_{i}"] = np.where(present, rng.uniform(-np.pi, np.pi, n), 0)
        e[f"lep_charge_{i}"] = np.full(n, 1 if i == 0 else -1)
        e[f"lep_type_{i}"] = rng.choice([11,13], n)
    return {k: np.asarray(v, dtype=np.int16 if k in INT_COLUMNS else np.float32) for k,v in e.items()}

def _write_npz(path, arrays):
    # NumPy's ZIP timestamps are fixed, so identical arrays produce identical bytes.
    np.savez_compressed(path, **arrays)

def checksums(path):
    path = Path(path)
    return {str(p.relative_to(path)).replace('\\','/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(path.rglob('*')) if p.is_file() and p.name != 'checksums.json'}

def generate_dataset(path, seed=42, mu=1., beta=1., pool_size=12000):
    if mu < 0 or beta <= 0 or pool_size < 600:
        raise ValueError("mu >= 0, beta > 0 and pool_size >= 600 required")
    path = Path(path)
    (path/'data').mkdir(parents=True, exist_ok=True)
    (path/'mc').mkdir(exist_ok=True)
    # Simulation independent of injected truth and data seed. Splits have unique events.
    rng = np.random.default_rng(20261013)
    parts = [_events(rng, pool_size//2, signal) for signal in (True, False)]
    pool = {k:np.concatenate([p[k] for p in parts]) for k in COLUMNS}
    n = len(pool['met_et'])
    pool['label'] = np.repeat([1,0], pool_size//2).astype(np.int16)
    pool['process'] = np.where(pool['label']==1, 345324, 363492).astype(np.int32)
    pool['event_id'] = np.arange(n,dtype=np.int64)
    pool['partition'] = np.zeros(n,dtype=np.int16)
    # Every process has train/validation/template samples and correct expected yields.
    for label in (0,1):
        idx = rng.permutation(np.flatnonzero(pool['label']==label))
        pool['partition'][idx[int(.6*len(idx)):int(.8*len(idx))]] = 1
        pool['partition'][idx[int(.8*len(idx)):]] = 2
    pool['weight'] = np.where(pool['label']==1, 350., 1600.)/(pool_size//2)
    rng = np.random.default_rng(seed)
    samples = [_events(rng, rng.poisson(mu*350), True), _events(rng, rng.poisson(beta*1600), False)]
    events = {k:np.concatenate([p[k] for p in samples]) for k in COLUMNS}
    # Identity is local to this dataset and must never encode a sealed RNG seed.
    events['event_id'] = np.arange(len(events['met_et']),dtype=np.int64) + 10**9
    meta = {'schema':'dataset-v1', 'origin':'synthetic teaching surrogate; not ATLAS data', 'generator':'higgslab.data.generate_dataset-v1', 'units':'GeV', 'lumi_fb':1000., 'signal_expected':350., 'background_expected':1600., 'partitions':{'0':'train','1':'validation','2':'templates'}, 'processes':{'345324':{'name':'toy HWW','label':1,'expected_events':350.},'363492':{'name':'toy continuum WW','label':0,'expected_events':1600.}}}
    _write_npz(path/'mc/pool.npz',pool)
    _write_npz(path/'data/events.npz',events)
    (path/'mc/pool_meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8',newline='\n')
    # Truth is returned to the trusted caller, never placed beside sandbox input.
    (path/'checksums.json').write_text(json.dumps(checksums(path),indent=2)+'\n',encoding='utf-8',newline='\n')
    return {'mu':float(mu),'beta':float(beta),'mH':125.,'seed':int(seed)}

def load_dataset(path):
    path = Path(path)
    def read(file):
        with np.load(file, allow_pickle=False) as archive:
            return {k:archive[k] for k in archive.files}
    events, pool = read(path/'data/events.npz'),read(path/'mc/pool.npz')
    meta = json.loads((path/'mc/pool_meta.json').read_text())
    if 'label' in events or 'weight' in events or 'truth' in events:
        raise ValueError('observation must not contain simulation labels, weights or truth')
    for table, required in ((events,COLUMNS+['event_id']),(pool,COLUMNS+['label','weight','process','event_id','partition'])):
        n = len(table['met_et'])
        for k in required:
            if k not in table or table[k].shape != (n,) or not np.isfinite(table[k]).all():
                raise ValueError(f"bad dataset column {k}")
        if n == 0:
            raise ValueError('empty dataset')
        if len(np.unique(table['event_id'])) != n:
            raise ValueError('duplicate event identity')
        if not np.isin(table['jet_n'],[0,1,2]).all():
            raise ValueError('jet_n must be 0, 1 or 2')
        if not np.issubdtype(table['event_id'].dtype,np.integer):
            raise ValueError('event identity must be integer')
        if np.any(table['met_et']<0):
            raise ValueError('negative MET')
        for i in range(2):
            if np.any(table[f'lep_pt_{i}']<=0) or np.any(table[f'jet_pt_{i}']<0):
                raise ValueError('invalid transverse momentum')
            if not np.isin(table[f'lep_charge_{i}'],[-1,1]).all() or not np.isin(table[f'lep_type_{i}'],[11,13]).all():
                raise ValueError('invalid lepton charge/type')
            absent = table['jet_n'] <= i
            if any(np.any(table[f'jet_{x}_{i}'][absent] != 0) for x in ('pt','eta','phi')):
                raise ValueError('nonzero padding')
    if set(np.unique(pool['label'])) != {0,1} or not set(np.unique(pool['partition'])) <= {0,1,2} or np.any(pool['weight'] <= 0):
        raise ValueError('labels, splits or weights invalid')
    for partition in (0,1,2):
        if set(pool['label'][pool['partition']==partition])!={0,1}:
            raise ValueError('each partition must contain both classes')
    if np.intersect1d(events['event_id'],pool['event_id']).size:
        raise ValueError('data / simulation event overlap')
    def row_keys(table):
        values=np.ascontiguousarray(np.column_stack([table[k] for k in FLOAT_COLUMNS]),dtype=np.float32)
        return values.view(np.dtype((np.void,values.dtype.itemsize*values.shape[1]))).ravel()
    if np.intersect1d(row_keys(events),row_keys(pool)).size:
        raise ValueError('data / simulation kinematic duplicate')
    # Detect derived duplicates across partitions, even if IDs were changed.
    rows = np.column_stack([pool[k] for k in FLOAT_COLUMNS])
    _, first, inverse = np.unique(rows,axis=0,return_index=True,return_inverse=True)
    if np.any(pool['partition'] != pool['partition'][first[inverse]]):
        raise ValueError('duplicate kinematics across partitions')
    for label,key in ((1,'signal_expected'),(0,'background_expected')):
        if not np.isclose(pool['weight'][pool['label']==label].sum(),meta[key]):
            raise ValueError('weight normalization mismatch')
    return events,pool,meta
