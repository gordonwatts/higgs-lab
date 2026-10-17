import importlib.util
from pathlib import Path
import shutil

from higgslab.contract import validate_result
from higgslab.data import generate_dataset


def test_submission_sidecar_model_runs_through_shared_fit(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    submission_dir = tmp_path / "submission"
    submission_dir.mkdir()
    analysis_copy = submission_dir / "analysis.py"
    shutil.copy2(repository / "submission" / "analysis.py", analysis_copy)
    shutil.copy2(repository / "solutions" / "models" / "classifier.json",
                 submission_dir / "model.json")
    spec = importlib.util.spec_from_file_location("test_student_analysis", analysis_copy)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    dataset = tmp_path / "dataset"
    generate_dataset(dataset, seed=91, mu=1.0, pool_size=600)
    output = tmp_path / "result"
    module.main(dataset, output)
    result = validate_result(output / "RESULT.json")
    assert next(p for p in result["pois"] if p["name"] == "mu")["total"] > 0
