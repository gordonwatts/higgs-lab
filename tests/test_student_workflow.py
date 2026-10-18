"""Rehearse a fresh full fork through an immutable submission export."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def test_fresh_student_clone_to_pinned_submission(tmp_path):
    source = Path(__file__).resolve().parents[1]
    checkout = tmp_path / "student"

    def git(*args, cwd=checkout):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, timeout=60)

    git("clone", "--quiet", "--no-hardlinks", str(source), str(checkout), cwd=tmp_path)
    env = {**os.environ, "PYTHONPATH": str(checkout / "src")}

    def cli(*args):
        return subprocess.run([sys.executable, "-m", "higgslab", *args], cwd=checkout,
                              env=env, check=True, capture_output=True, text=True, timeout=180)

    cli("run", "datasets/public", "output/reference")
    analysis = checkout / "submission/analysis.py"
    analysis.write_text(analysis.read_text().replace("background_unc=.10", "background_unc=.15"),
                        encoding="utf-8", newline="\n")
    cli("check")
    reference = json.loads((checkout / "output/reference/RESULT.json").read_text())
    changed = json.loads((checkout / "output/check/submission/first/RESULT.json").read_text())
    assert changed != reference, "The editable submission must exercise the student's change"
    cli("train", "datasets/public", "output/model.json", "--mode", "classifier", "--epochs", "1")
    cli("run", "datasets/public", "output/classifier", "--model", "output/model.json")
    cli("score-local", "--submission", "submission", "--output", "output/suite", "--count", "6")
    assert json.loads((checkout / "output/suite/metrics.json").read_text())["failures"] == 0
    git("add", "submission/analysis.py")
    git("-c", "user.name=Student rehearsal", "-c", "user.email=student@example.invalid",
        "-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "Change background constraint")
    sha = git("rev-parse", "HEAD").stdout.decode().strip()
    line = cli("submission-line", "--repo", "https://github.com/example-student/higgs-lab").stdout.strip()
    assert line == f"team: https://github.com/example-student/higgs-lab @ {sha}"
    pinned = tmp_path / "pinned"
    pinned.mkdir()
    archive = git("archive", "--format=zip", sha, "submission").stdout
    with zipfile.ZipFile(io.BytesIO(archive)) as snapshot:
        snapshot.extractall(pinned)
    assert {p.name for p in pinned.iterdir()} == {"submission"}
    assert (pinned / "submission/analysis.py").read_bytes() == analysis.read_bytes()
    cli("check", "--submission", str(pinned / "submission"), "--output", "output/pinned-check")
    exported = json.loads((checkout / "output/pinned-check/submission/first/RESULT.json").read_text())
    assert exported == changed
