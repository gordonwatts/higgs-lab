"""Print a pinned submission line; posting remains an explicit student action."""
import re
import subprocess
from urllib.parse import urlparse

def submission_line(repository=None,team=None):
    def git(*args):
        return subprocess.run(['git',*args],check=True,capture_output=True,text=True,timeout=30).stdout.strip()
    if git('status','--porcelain'):
        raise ValueError('commit your changes before generating a submission line')
    sha=git('rev-parse','--verify','HEAD')
    if not re.fullmatch('[0-9a-fA-F]{40}',sha): raise ValueError('full Git commit SHA required')
    repository=repository or git('remote','get-url','origin')
    if repository.startswith('git@github.com:'):
        repository='https://github.com/'+repository.split(':',1)[1]
    repository=repository.removesuffix('.git').rstrip('/')
    parsed=urlparse(repository)
    if parsed.scheme!='https' or parsed.netloc!='github.com' or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',parsed.path):
        raise ValueError('use a public https://github.com/OWNER/FORK repository')
    if team is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',team):
        raise ValueError('team names may contain 1–64 letters, digits, dots, hyphens and underscores')
    return f'team: {team+" " if team else ""}{repository} @ {sha.lower()}'
