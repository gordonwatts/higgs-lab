"""Independent converter for the pinned course ROOT schema (not a download tool).

Usage: python scripts/prepare_root.py INPUT.root OUTPUT --seed 42
Requires the dev extra. Input redistribution rights must be checked separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import uproot
from higgslab.data import COLUMNS,INT_COLUMNS,checksums,load_dataset

def convert(source,output,seed=42):
    source,output=Path(source),Path(output)
    with uproot.open(source) as f:
        a=f[f.keys()[0]].arrays(library='np')
    valid=(a['lep_n']==2)&(a['mcWeight']>0)
    ids=np.flatnonzero(valid).astype(np.int64)
    a={k:v[valid] for k,v in a.items()}
    table={k:np.asarray(a[k],dtype=np.int16 if k in INT_COLUMNS else np.float32) for k in COLUMNS}
    # This reduced ROOT table already stores pt and MET in GeV, E in MeV.
    # Ignore E and recompute massless E from GeV pt/eta in the canonical tokens.
    table['jet_n']=np.clip(table['jet_n'],0,2)
    for i in range(2):
        missing=(table['jet_n']<=i)|(table[f'jet_pt_{i}']<0)
        for x in ('pt','eta','phi'): table[f'jet_{x}_{i}'][missing]=0
    table['event_id']=ids
    table['label']=a['label'].astype(np.int16)
    table['process']=a['channelNumber'].astype(np.int32)
    rng=np.random.default_rng(seed)
    assignments=np.empty(len(ids),dtype=np.int16)
    expected={345323:39.83,345324:578.11,363492:15968.85}
    weights=np.zeros(len(ids))
    for process,yield_ in expected.items():
        idx=rng.permutation(np.flatnonzero(table['process']==process))
        if len(idx)<100: raise ValueError(f'missing process {process}')
        # Disjoint source reservoir for pseudo-data. No source row reused in MC.
        splits=np.array_split(idx,10)
        for j,split in enumerate(splits): assignments[split]=0 if j<5 else 1 if j<7 else 2 if j<9 else 3
        is_mc=(table['process']==process)&(assignments!=3)
        weights[is_mc]=a['mcWeight'][is_mc]/a['mcWeight'][is_mc].sum()*yield_
    if not np.all(np.isin(table['process'],list(expected))): raise ValueError('unrecognized process')
    table['weight']=weights
    table['partition']=assignments
    pool={k:v[assignments!=3] for k,v in table.items()}
    data_indices=[]
    for process,yield_ in expected.items():
        idx=np.flatnonzero((assignments==3)&(table['process']==process))
        count=rng.poisson(yield_)
        # This reservoir is large enough to sample without replacement, preserving identities.
        if count>len(idx): raise ValueError('not enough independent pseudo-data events')
        data_indices.extend(rng.choice(idx,count,replace=False,p=a['mcWeight'][idx]/a['mcWeight'][idx].sum()))
    data_indices=np.asarray(data_indices,dtype=int)
    events={k:table[k][data_indices] for k in COLUMNS+['event_id']}
    (output/'mc').mkdir(parents=True,exist_ok=True); (output/'data').mkdir(exist_ok=True)
    np.savez_compressed(output/'mc/pool.npz',**pool); np.savez_compressed(output/'data/events.npz',**events)
    meta={'schema':'dataset-v1','origin':'course reduced ATLAS simulation; instructor must establish release/license before redistribution','source_commit':'86fb86c62108cae88a92f75b0f7268a9130a0aec','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'units':'GeV','input_units':{'pt':'GeV','met':'GeV','E':'MeV (ignored; massless reconstruction)'},'signal_expected':617.94,'background_expected':15968.85,'lumi_fb':1000.,'normalization':'published benchmark yields, not independently derived cross sections','processes':{str(k):{'expected_events':v} for k,v in expected.items()},'public_truth':{'mu':1.,'beta':1.,'mH':125.},'seed':seed}
    (output/'mc/pool_meta.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8',newline='\n')
    load_dataset(output)
    (output/'checksums.json').write_text(json.dumps(checksums(output),indent=2)+'\n',encoding='utf-8',newline='\n')
    return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source'); p.add_argument('output'); p.add_argument('--seed',type=int,default=42)
    args=p.parse_args(); print(json.dumps(convert(args.source,args.output,args.seed),indent=2))
