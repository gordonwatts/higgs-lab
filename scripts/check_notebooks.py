"""Execute short notebooks in temporary directories; committed output stays empty."""
import os
from pathlib import Path
import tempfile
import asyncio
import nbformat
from nbclient import NotebookClient

root=Path(__file__).resolve().parents[1]
if os.name=='nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
for path in sorted((root/'notebooks').glob('*.ipynb')):
    notebook=nbformat.read(path,as_version=4)
    for cell in notebook.cells:
        if cell.cell_type=='code':
            assert not cell.outputs and cell.execution_count is None, f'clear outputs: {path}'
    NotebookClient(notebook,timeout=300,kernel_name='python3',resources={'metadata':{'path':str(root)}}).execute()
    print(f'PASS {path.name}')
