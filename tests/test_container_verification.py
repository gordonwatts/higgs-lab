import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_container_paths.py"
SPEC = importlib.util.spec_from_file_location("verify_container_paths", SCRIPT)
verify_container_paths = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_container_paths)


def test_suite_points_reproducible_and_mix_null_signal_and_beta():
    first = verify_container_paths.suite_points(12, 711)
    assert first == verify_container_paths.suite_points(12, 711)
    assert {mu for _, mu, _ in first} >= {0.0, 0.5, 1.0, 1.5, 2.0}
    assert len({beta for _, _, beta in first}) > 1
    assert len({seed for seed, _, _ in first}) == len(first)
    with pytest.raises(ValueError, match="at least 6"):
        verify_container_paths.suite_points(5, 711)


def test_snapshot_contains_only_student_entrypoint_and_optional_model(tmp_path):
    model = tmp_path / "reference.json"
    model.write_text("{}", encoding="utf-8")
    snapshot = verify_container_paths.prepare_snapshot(tmp_path / "with-model", model)
    assert {path.name for path in snapshot.iterdir()} == {"analysis.py", "run.sh", "model.json"}
    assert (snapshot / "model.json").read_text(encoding="utf-8") == "{}"
    starter = verify_container_paths.prepare_snapshot(tmp_path / "starter")
    assert {path.name for path in starter.iterdir()} == {"analysis.py", "run.sh"}
