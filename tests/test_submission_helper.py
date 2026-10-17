import subprocess
from types import SimpleNamespace
import pytest
from higgslab.submission import submission_line

def test_line_contains_exact_sha_and_normalized_fork(monkeypatch):
    def git(args,**kwargs):
        values={('status','--porcelain'):'',('rev-parse','--verify','HEAD'):'a'*40,('remote','get-url','origin'):'git@github.com:student/higgs-lab.git'}
        return SimpleNamespace(stdout=values[tuple(args[1:])])
    monkeypatch.setattr(subprocess,'run',git)
    assert submission_line()=='team: https://github.com/student/higgs-lab @ '+'a'*40

def test_dirty_tree_is_refused(monkeypatch):
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=' M submission/analysis.py'))
    with pytest.raises(ValueError,match='commit'): submission_line()
