"""Write public workshop links without putting any credential in the site."""
import argparse
import json
import os
from pathlib import Path
import re
import tomllib
from urllib.parse import urlparse

def write_config(output='site',config_path='workshop.toml',environment=None):
    env=os.environ if environment is None else environment
    path=Path(config_path)
    config=tomllib.loads(path.read_text()).get('workshop',{}) if path.exists() else {}
    repository=env.get('GITHUB_REPOSITORY','')
    if repository and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('invalid public repository name')
    server=env.get('GITHUB_SERVER_URL','https://github.com').rstrip('/')
    server_parts=urlparse(server)
    if server_parts.scheme!='https' or not server_parts.hostname or server_parts.username or server_parts.password:
        raise ValueError('invalid public GitHub server')
    issue=env.get('SUBMISSIONS_ISSUE','').strip()
    pages=env.get('PAGES_URL','').strip()
    if pages:
        parsed=urlparse(pages)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('invalid public Pages URL')
    result={
        'event_title':env.get('EVENT_TITLE') or config.get('event_title','HiggsLab: From Events to Evidence'),
        'workshop_name':env.get('WORKSHOP_NAME') or config.get('name',''),
        'repository_url':f'{server}/{repository}' if repository else None,
        'submissions_url':f'{server}/{repository}/issues/{issue}' if repository and issue.isdigit() else None,
        'pages_url':pages or None,
    }
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    (output/'workshop.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',default='site'); p.add_argument('--config',default='workshop.toml')
    args=p.parse_args(); write_config(args.output,args.config)
