"""Check local Markdown links in README and docs without depending on hosting."""
from pathlib import Path
import re
from urllib.parse import unquote,urlsplit

root=Path(__file__).resolve().parents[1]
errors=[]
for path in [root/'README.md',*sorted((root/'docs').glob('*.md'))]:
    text=path.read_text(encoding='utf-8')
    for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
        target=target.split(' "')[0].strip('<>')
        url=urlsplit(target)
        if url.scheme or url.netloc or not url.path or '{' in url.path: continue
        dest=(path.parent/unquote(url.path)).resolve()
        if not dest.exists(): errors.append(f'{path.relative_to(root)}: {target}')
if errors: raise SystemExit('\n'.join(errors))
print('PASS: README and documentation local links')
