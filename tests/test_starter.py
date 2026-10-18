from pathlib import Path
from higgslab.check import check_submission

def test_real_starter_contract(tmp_path):
    root=Path(__file__).resolve().parents[1]
    result=check_submission(root/'submission',root/'datasets/public',tmp_path/'check')
    assert result['pois'][0]['total']>0
