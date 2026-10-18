import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('site_config',Path(__file__).resolve().parents[1]/'scripts/site_config.py')
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

def test_new_workshop_links_only_public_fields(tmp_path):
    result=module.write_config(tmp_path,environment={'GITHUB_REPOSITORY':'newowner/newcohort','SUBMISSIONS_ISSUE':'27','SEALED_SEED':'never-publish','GH_TOKEN':'never-publish','PAGES_URL':'https://newowner.github.io/newcohort/'})
    assert result['submissions_url']=='https://github.com/newowner/newcohort/issues/27'
    assert 'never-publish' not in (tmp_path/'workshop.json').read_text()

def test_rejects_credentials_in_public_urls(tmp_path):
    with pytest.raises(ValueError): module.write_config(tmp_path,environment={'PAGES_URL':'https://user:secret@example.org/'})

def test_preview_without_pages_keeps_repository_link(tmp_path):
    result=module.write_config(tmp_path,environment={'GITHUB_REPOSITORY':'newowner/newcohort','PAGES_URL':''})
    assert result['repository_url']=='https://github.com/newowner/newcohort'
    assert result['pages_url'] is None
    assert result['submissions_url'] is None
