"""Keep deployment files parseable and disabled in unconfigured student forks."""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

def test_workflow_syntax_and_hosted_gates():
    workflows={path.stem:yaml.load(path.read_text(),Loader=yaml.BaseLoader) for path in (ROOT/'.github/workflows').glob('*.yml')}
    assert all('on' in workflow and 'jobs' in workflow for workflow in workflows.values())
    scorer=workflows['score-submission']
    assert 'WORKSHOP_ENABLED' in scorer['jobs']['score']['if']
    assert 'SUBMISSIONS_OPEN' in scorer['jobs']['score']['if']
    assert 'WORKSHOP_CONFIGURED' in scorer['jobs']['publish']['if']
    assert scorer['jobs']['score']['permissions'].get('contents')=='read'
    assert 'pages' not in scorer['jobs']['score']['permissions']
    docs=workflows['docs']
    assert 'WORKSHOP_CONFIGURED' in docs['jobs']['publish']['if']
