import json
from pathlib import Path

from evaluator import github_event
from evaluator.state import EvaluationStore


SHA = "a" * 40


def _event(path, *, author, repository="example/team-a", body=None, created_at="2026-10-16T12:00:00Z"):
    path.write_text(json.dumps({
        "repository": {"full_name": "workshop/higgs-lab"},
        "issue": {"number": 7},
        "comment": {
            "user": {"login": author},
            "created_at": created_at,
            "body": body or f"team: https://github.com/{repository} @ {SHA}",
        },
    }), encoding="utf-8")


def _run(monkeypatch, tmp_path, *, author, repository="example/team-a", created_at="2026-10-16T12:00:00Z"):
    event_path, output_path = tmp_path / "event.json", tmp_path / "output.txt"
    _event(event_path, author=author, repository=repository, created_at=created_at)
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("SUBMISSIONS_ISSUE", "7")
    monkeypatch.setenv("SUBMISSION_DEADLINE", "2026-10-16")
    monkeypatch.setenv("GITHUB_REPOSITORY", "workshop/higgs-lab")
    monkeypatch.setenv("EVALUATOR_STATE_DIR", str(tmp_path / "state"))
    return github_event.main(), output_path.read_text(encoding="utf-8")


def test_event_accepts_owner_claim_and_pins_first_author(monkeypatch, tmp_path):
    status, output = _run(monkeypatch, tmp_path, author="example")
    assert status == 0
    assert "valid=true" in output and "team=example" in output

    store = EvaluationStore(tmp_path / "claims.sqlite", tmp_path / "claims.json")
    assert store.claim_team("team-a", "example/team-a", "example")
    assert store.claim_team("team-a", "example/team-a", "example")
    assert not store.claim_team("team-a", "example/team-a", "other")
    assert not store.claim_team("team-a", "different/team-a", "different")


def test_event_requires_repository_owner_and_submission_timestamp(monkeypatch, tmp_path):
    status, output = _run(monkeypatch, tmp_path, author="someone-else")
    assert status == 1 and "valid=false" in output and "invalid_reason=ownership" in output

    late = tmp_path / "late"
    late.mkdir()
    status, output = _run(monkeypatch, late, author="example", created_at="2026-10-17T00:00:00Z")
    assert status == 1 and "invalid_reason=malformed" in output
