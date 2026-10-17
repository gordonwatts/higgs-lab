from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import threading

import pytest

from evaluator.scoring import make_sealed_suite, summarize
from evaluator.security import SandboxError, _copy_safe_tree, run_in_docker
from evaluator.state import EvaluationStore
from evaluator.submission import SubmissionError, parse_submission


def result(mu, uncertainty=0.2, significance=2.0, discovery=False):
    return {"pois": [{"name": "mu", "value": mu, "stat": uncertainty, "syst": 0,
                      "total": uncertainty}], "significance_obs": significance,
            "discovery": discovery}


def test_parse_canonical_and_named_submission_lines():
    sha = "A" * 40
    parsed = parse_submission(f"team: https://github.com/example/student @ {sha}")
    assert (parsed.team, parsed.repository, parsed.sha) == ("example", "example/student", "a" * 40)
    other_owner = parse_submission(f"team: https://github.com/second-owner/student @ {sha}")
    assert other_owner.team == "second-owner"
    named = parse_submission(f"team: Delhi-A https://github.com/example/student @ {sha}")
    assert named.team == "Delhi-A"
    with pytest.raises(SubmissionError):
        parse_submission("team: X https://github.com/example/student @ " + "a" * 7)
    with pytest.raises(SubmissionError):
        parse_submission("team: https://github.com/example/student.git @ " + "a" * 40)
    with pytest.raises(SubmissionError):
        parse_submission(f"team: https://github.com/example/a @ {sha}\nteam: https://github.com/example/b @ {sha}")


def test_snapshot_rejects_symlink_and_data_but_copies_code(tmp_path):
    source, destination = tmp_path / "submission", tmp_path / "snapshot"
    source.mkdir(); destination.mkdir()
    (source / "run.sh").write_text("#!/bin/bash\necho ok\n")
    _copy_safe_tree(source, destination)
    assert (destination / "run.sh").read_text().endswith("echo ok\n")

    bad_source, bad_target = tmp_path / "bad-submission", tmp_path / "bad-target"
    bad_source.mkdir(); bad_target.mkdir()
    (bad_source / "events.npz").write_bytes(b"data")
    with pytest.raises(SandboxError, match="data files"):
        _copy_safe_tree(bad_source, bad_target)

    model_source, model_target = tmp_path / "model-source", tmp_path / "model-target"
    model_source.mkdir(); model_target.mkdir()
    (model_source / "weights.pt").write_bytes(b"binary model")
    with pytest.raises(SandboxError, match="data files"):
        _copy_safe_tree(model_source, model_target)

    symlink_source, symlink_target = tmp_path / "link-submission", tmp_path / "link-target"
    symlink_source.mkdir(); symlink_target.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    try:
        (symlink_source / "run.sh").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(SandboxError, match="symlink"):
        _copy_safe_tree(symlink_source, symlink_target)


def test_snapshot_per_file_and_total_size_limits(tmp_path, monkeypatch):
    import evaluator.security as security
    source, destination = tmp_path / "submission", tmp_path / "snapshot"
    source.mkdir(); destination.mkdir()
    (source / "run.sh").write_text("12345")
    monkeypatch.setattr(security, "MAX_FILE_BYTES", 4)
    with pytest.raises(SandboxError, match="size limit"):
        _copy_safe_tree(source, destination)


def test_score_v1_metrics_suite_determinism_and_gates():
    suite1 = make_sealed_suite("a" * 64)
    suite2 = make_sealed_suite("a" * 64)
    assert suite1 == suite2 and len(suite1) == 30
    assert len({seed for seed, _, _ in suite1}) == 30
    assert {mu for _, mu, _ in suite1} <= {0.0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0}
    assert sum(1 for _, mu, _ in suite1 if mu == 0) == 10
    assert len({beta for _, _, beta in suite1}) > 1
    truths = [0, 1, 2, 0, 1, 2]
    fitted = [0.1, 0.9, 2.0, 0.2, 0.9, 2.0]
    results = [result(mu, discovery=(t > 0)) for mu, t in zip(fitted, truths)]
    baseline = [result(t + (0.5 if t else 0.1)) for t in truths]
    summary = summarize(results, truths, baseline_results=baseline, total_cases=6)
    assert summary["mu_bias"] == pytest.approx(1 / 60)
    assert summary["mu_recovery_slope"] == pytest.approx(0.925)
    assert summary["pull_width"] > 0
    assert summary["failures"] == 0
    assert summary["false_discovery_rate"] == pytest.approx(0)
    assert summary["discovery_power"] == pytest.approx(1)
    assert summary["score"] > 0 and summary["rankable"] is True
    insufficient = summarize(results[:2], truths[:2], total_cases=6)
    assert insufficient["rankable"] is False and insufficient["score"] == 0


def test_store_two_teams_resubmission_invalid_cache_and_race(tmp_path):
    store = EvaluationStore(tmp_path / "state.sqlite", tmp_path / "leaderboard.json")
    store.set_baseline({"mu_rms_residual": 0.4})
    store.record("Delhi", "one/team", "a" * 40, "suite-v1", "complete", result(1))
    store.record("Delhi", "one/team", "b" * 40, "suite-v1", "failed", error="fixture error")
    store.record("Mumbai", "two/team", "c" * 40, "suite-v1", "complete", result(0.9))
    store.record("new-user", "", "", "submission-v1", "invalid", error="Malformed submission")
    assert store.cached_result("one/team", "a" * 40, "suite-v1")["pois"][0]["value"] == 1
    assert store.cached_result("one/team", "b" * 40, "suite-v1") is None
    failures = []
    gate = threading.Barrier(12)

    def add(i):
        try:
            gate.wait()
            store.record(f"team-{i}", f"o/r{i}", f"{i:040x}", "suite-v1", "complete", result(1 + i / 10))
        except Exception as exc:
            failures.append(exc)

    with ThreadPoolExecutor(max_workers=12) as pool:
        list(pool.map(add, range(12)))
    assert not failures
    payload = json.loads((tmp_path / "leaderboard.json").read_text())
    assert len(payload["latest"]) == 15
    assert len(payload["history"]) == 16
    assert payload["baseline"][0]["team"] == "HiggsLab baseline"
    assert all("suite-v1" not in row for row in payload["history"])
    assert any(row["team"] == "Delhi" and row["status"] == "failed" for row in payload["latest"])
    assert any(row["team"] == "new-user" and row["status"] == "invalid" for row in payload["latest"])


def test_malformed_submission_selects_current_sealed_suite(tmp_path, monkeypatch):
    from evaluator.__main__ import main
    state_dir = tmp_path / "state"
    store = EvaluationStore(state_dir / "evaluation.sqlite", state_dir / "leaderboard.json")
    store.set_active_suite("prior-suite")
    store.record("prior-team", "owner/prior", "a" * 40, "prior-suite", "complete", result(1))
    monkeypatch.setenv("SEALED_SEED", "current-secret")
    assert main(["record-invalid", "--team", "new-user", "--state-dir", str(state_dir)]) == 0
    payload = json.loads((state_dir / "leaderboard.json").read_text())
    assert [row["team"] for row in payload["latest"]] == ["new-user"]
    assert {row["suite_scope"] for row in payload["history"]} == {"active", "prior suite"}


def test_active_suite_separates_current_leaderboard_and_final_cohort(tmp_path):
    store = EvaluationStore(tmp_path / "state.sqlite", tmp_path / "leaderboard.json")
    store.set_active_suite("suite-a")
    store.set_baseline({"suite": "a"}, suite_id="suite-a")
    store.record("Alpha", "owner/alpha", "a" * 40, "suite-a", "complete", result(1.0))
    store.record("Beta", "owner/beta", "b" * 40, "suite-b", "complete", result(1.0))

    store.set_active_suite("suite-b")
    payload = json.loads((tmp_path / "leaderboard.json").read_text())
    assert [row["team"] for row in payload["latest"]] == ["Beta"]
    assert payload["baseline"] == []
    assert {row["suite_scope"] for row in payload["history"]} == {"active", "prior suite"}
    assert [row["team"] for row in store.latest_submissions()] == ["Beta"]

    store.set_baseline({"suite": "b"}, suite_id="suite-b")
    store.set_active_suite("suite-a")
    payload = json.loads((tmp_path / "leaderboard.json").read_text())
    assert [row["team"] for row in payload["latest"]] == ["Alpha"]
    assert payload["baseline"][0]["result"] == {"suite": "a"}


def test_evaluator_cache_suite_id_tracks_seed_code_and_optional_cohort(monkeypatch):
    import evaluator.hosted as hosted
    monkeypatch.setattr(hosted, "evaluator_fingerprint", lambda: "code-a")
    first = hosted.make_suite_id("secret", cohort_id="workshop-a")
    assert hosted.make_suite_id("secret", cohort_id="workshop-a") == first
    assert hosted.make_suite_id("other-secret", cohort_id="workshop-a") != first
    assert hosted.make_suite_id("secret", cohort_id="workshop-b") != first
    monkeypatch.setattr(hosted, "evaluator_fingerprint", lambda: "code-b")
    assert hosted.make_suite_id("secret", cohort_id="workshop-a") != first


def test_docker_runner_supplies_confinement_and_collects_regular_result(tmp_path, monkeypatch):
    snapshot, dataset, output = tmp_path / "snapshot", tmp_path / "data", tmp_path / "output"
    snapshot.mkdir(); dataset.mkdir(); output.mkdir()
    (snapshot / "run.sh").write_text("#!/bin/bash\n")
    calls = []
    valid = '{"pois":[],"significance_obs":0,"discovery":false}'

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        if "python" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout=valid.encode(), stderr=b"")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr("evaluator.security.subprocess.run", fake_run)
    run_in_docker(snapshot, dataset, output, timeout_seconds=5)
    run_command, run_kwargs = calls[0]
    assert "--network=none" in run_command and "--read-only" in run_command
    assert "--cap-drop=ALL" in run_command and "--security-opt=no-new-privileges" in run_command
    assert "--memory=6g" in run_command and "--pull=never" in run_command
    assert "--detach" in run_command and "--log-driver=none" in run_command
    assert "--user=0:0" in run_command and run_command[-2:] == ["sleep", "infinity"]
    assert "--mount" in run_command and all("readonly" in arg for arg in run_command if arg.startswith("type=bind"))
    assert not any(arg in {"-e", "--env", "-v"} or "/var/run/docker.sock" in arg for arg in run_command)
    assert run_kwargs.get("stdout") == subprocess.DEVNULL and run_kwargs.get("stderr") == subprocess.DEVNULL
    student_call = calls[1][0]
    assert student_call[0:4] == ["docker", "exec", "--user=65534:65534", "--workdir=/submission"]
    assert student_call[-4:] == ["bash", "/submission/run.sh", "/data", "/output"]
    assert calls[2][0][0:3] == ["docker", "exec", "--user=0:0"]
    assert calls[-1][0][1:3] == ["rm", "--force"]
    assert (output / "RESULT.json").read_text() == valid


def test_docker_rejects_symlink_result_and_unavailable_docker(tmp_path, monkeypatch):
    snapshot, dataset, output = tmp_path / "snapshot", tmp_path / "data", tmp_path / "output"
    snapshot.mkdir(); dataset.mkdir(); output.mkdir()
    (snapshot / "run.sh").write_text("#!/bin/bash\n")
    def symlink_result(cmd, **kwargs):
        if "python" in cmd:
            return subprocess.CompletedProcess(cmd, 3)
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")
    monkeypatch.setattr("evaluator.security.subprocess.run", symlink_result)
    with pytest.raises(SandboxError, match="regular file"):
        run_in_docker(snapshot, dataset, output)

    output2 = tmp_path / "output2"; output2.mkdir()
    def unavailable(*args, **kwargs):
        raise FileNotFoundError("docker")
    monkeypatch.setattr("evaluator.security.subprocess.run", unavailable)
    with pytest.raises(FileNotFoundError):
        run_in_docker(snapshot, dataset, output2)
