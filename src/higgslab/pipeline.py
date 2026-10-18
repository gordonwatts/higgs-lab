"""Stable load → features/score → templates → fit → result seams."""
import json
from pathlib import Path
from .data import load_dataset
from .templates import build
from .fit import fit
from .contract import validate_result

def run(dataset_dir, output_dir, model_path=None, bins=None):
    events,pool,meta = load_dataset(dataset_dir)
    scorer=None
    if model_path is not None:
        from .training import score
        scorer=lambda e:score(e,model_path)
    result=fit(build(events,pool,meta,scorer,bins))
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=True)
    path=output/'RESULT.json'
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    validate_result(path)
    return result
