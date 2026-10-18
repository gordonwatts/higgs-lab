from pathlib import Path
import pytest
from higgslab.contract import validate_result

@pytest.mark.parametrize('text',['[]','{"pois":[null]}','{"pois":[],"pois":[]}', '{"extra":1e309}', '{"pois":[1]}'])
def test_malformed_json_is_rejected(tmp_path,text):
    path=tmp_path/'RESULT.json'; path.write_text(text)
    with pytest.raises(ValueError): validate_result(path)

def test_seed_is_not_in_input_identifiers(tmp_path):
    from higgslab.data import generate_dataset,load_dataset
    generate_dataset(tmp_path,2**64-1)
    e,_,meta=load_dataset(tmp_path)
    assert e['event_id'][0]==10**9
    assert 'seed' not in meta

def test_rejects_symlink_result(tmp_path):
    import os
    if os.name=='nt': pytest.skip('Windows symlink privilege unavailable')
    real=tmp_path/'file'; real.write_text('{}')
    link=tmp_path/'RESULT.json'; link.symlink_to(real)
    with pytest.raises(ValueError): validate_result(link)
