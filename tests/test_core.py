import json
import numpy as np
import pytest
from higgslab.data import generate_dataset,load_dataset,checksums
from higgslab.features import tokens,token_mask,engineered
from higgslab.pipeline import run
from higgslab.contract import validate_result

def test_generator_reproducible_and_separated(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b'
    generate_dataset(a,31); generate_dataset(b,31)
    assert checksums(a)==checksums(b)
    e,p,m=load_dataset(a)
    assert not set(e['event_id']) & set(p['event_id'])
    assert set(p['partition'])=={0,1,2}
    assert np.isclose(p['weight'][p['label']==1].sum(),m['signal_expected'])
    t=tokens(p); mask=token_mask(p)
    assert t.shape==(12000,5,4)
    assert np.all(t[~mask]==0)
    np.testing.assert_allclose(np.linalg.norm(t[:,0,:2],axis=1),p['lep_pt_0'],rtol=1e-6)
    assert np.isfinite(engineered(e)).all()

@pytest.mark.parametrize('mu',[0.,1.,1.7])
def test_measurement_recovers_signal(tmp_path,mu):
    path=tmp_path/'data'; generate_dataset(path,100,mu)
    result=run(path,tmp_path/'one')
    poi=result['pois'][0]
    assert abs(poi['value']-mu)<4*poi['total']
    assert result==run(path,tmp_path/'two')
    assert result['interval_mu'][0]<poi['value']<result['interval_mu'][1]

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),True])
def test_result_rejects_invalid_numbers(tmp_path,bad):
    path=tmp_path/'RESULT.json'
    path.write_text(json.dumps({'pois':[{'name':'mu','value':bad,'stat':1,'syst':0,'total':1}],'significance_obs':1,'discovery':False}))
    with pytest.raises(ValueError): validate_result(path)

def test_validation_rejects_kinematic_leakage(tmp_path):
    generate_dataset(tmp_path,1)
    _,p,_=load_dataset(tmp_path)
    from higgslab.data import FLOAT_COLUMNS
    target=np.flatnonzero(p['partition']!=p['partition'][0])[0]
    for k in FLOAT_COLUMNS: p[k][target]=p[k][0]
    np.savez_compressed(tmp_path/'mc/pool.npz',**p)
    with pytest.raises(ValueError,match='duplicate kinematics'): load_dataset(tmp_path)

def test_validation_rejects_copied_observation_with_changed_id(tmp_path):
    generate_dataset(tmp_path,1)
    e,p,_=load_dataset(tmp_path)
    from higgslab.data import COLUMNS
    for key in COLUMNS: e[key][0]=p[key][0]
    np.savez_compressed(tmp_path/'data/events.npz',**e)
    with pytest.raises(ValueError,match='kinematic duplicate'): load_dataset(tmp_path)
