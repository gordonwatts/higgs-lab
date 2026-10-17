"""Run your own trusted starter twice locally. Hosted submissions use Docker."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from .contract import validate_result

def check_submission(submission='submission',dataset='datasets/public',output='output/check-submission'):
    submission,dataset,output=map(lambda p:Path(p).resolve(),(submission,dataset,output))
    if not (submission/'run.sh').is_file():
        raise ValueError('submission/run.sh is required')
    results=[]
    for name in ('first','second'):
        dest=output/name
        dest.mkdir(parents=True,exist_ok=True)
        if any(dest.iterdir()):
            # Never accept stale output from an earlier successful execution.
            for p in dest.iterdir():
                if p.is_file() or p.is_symlink(): p.unlink()
                else: raise ValueError('check output must not contain subdirectories')
        bash=shutil.which('bash')
        if os.name=='nt':
            # Windows/WSL bash may not have access to the Windows venv. The
            # starter's Python entrypoint is equivalent; custom shell requires Linux.
            if not (submission/'analysis.py').is_file():
                raise ValueError('custom shell submissions require Linux/Bash for local checking')
            command=[sys.executable,str(submission/'analysis.py'),str(dataset),str(dest)]
        elif bash:
            command=[bash,str(submission/'run.sh'),str(dataset),str(dest)]
        else:
            raise ValueError('Bash is required to check run.sh')
        subprocess.run(command,check=True,timeout=600,cwd=submission)
        results.append(validate_result(dest/'RESULT.json'))
    if results[0]!=results[1]:
        raise ValueError('submission is not deterministic')
    return results[0]
