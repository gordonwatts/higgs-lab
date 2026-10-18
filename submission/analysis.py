"""Editable student analysis. The common runtime provides higgslab."""
import json
import sys
from pathlib import Path
from higgslab.data import load_dataset
from higgslab.templates import build
from higgslab.fit import fit
from higgslab.contract import validate_result

def main(dataset, output):
    model_path = Path(__file__).with_name('model.json')
    if model_path.is_file():
        # A submitted classifier travels beside this script as portable JSON.
        # The evaluator invokes run.sh with only dataset and output paths.
        from higgslab.pipeline import run
        run(dataset, output, model_path=model_path)
        return
    events,pool,meta=load_dataset(dataset)
    # TODO: change just one component, then compare the same local suite.
    templates=build(events,pool,meta)
    result=fit(templates,background_unc=.10)
    dest=Path(output); dest.mkdir(parents=True,exist_ok=True)
    path=dest/'RESULT.json'
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    validate_result(path)

if __name__=='__main__':
    main(*sys.argv[1:])
