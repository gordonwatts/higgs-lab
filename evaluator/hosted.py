"""Trusted-side orchestration for one immutable workshop submission."""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import time

from .scoring import make_sealed_suite, summarize, SUITE_SIZE
from .security import SandboxError, run_in_docker, snapshot_commit
from .submission import Submission
from .state import EvaluationStore


SUITE_ID = "sealed-suite-v1"
MAX_SUBMISSION_WALL_SECONDS = 1_500


def evaluator_fingerprint() -> str:
    """Hash trusted code and dependency declarations that can change score meaning."""
    evaluator_dir = Path(__file__).resolve().parent
    root = evaluator_dir.parent
    package_spec = importlib.util.find_spec("higgslab")
    package_dirs = [Path(entry).resolve() for entry in (package_spec.submodule_search_locations or ())] if package_spec else []
    package_dir = next((path for path in package_dirs if path.is_dir()), root / "src" / "higgslab")
    paths = [*evaluator_dir.glob("*.py"), *package_dir.glob("*.py"),
             root / "pyproject.toml", root / "uv.lock", root / "evaluator" / "Dockerfile",
             root / "evaluator" / "requirements-sandbox.txt"]
    digest = hashlib.sha256()
    unique = {path.resolve() for path in paths if path.is_file()}
    def path_label(path: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return f"installed/{path.parent.name}/{path.name}"
    for path in sorted(unique, key=path_label):
        relative = path_label(path).encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big")); digest.update(relative)
        digest.update(len(content).to_bytes(8, "big")); digest.update(content)
    return digest.hexdigest()


def make_suite_id(sealed_seed: str, *, cohort_id: str | None = None) -> str:
    """Version the sealed sample by seed, trusted evaluator code, and optional cohort marker."""
    seed_tag = hashlib.sha256(sealed_seed.encode()).hexdigest()
    evaluator_tag = evaluator_fingerprint()
    cohort = cohort_id if cohort_id is not None else os.environ.get("HIGGSLAB_COHORT_ID", "")
    cohort_tag = hashlib.sha256(cohort.encode()).hexdigest() if cohort else "default"
    return f"{SUITE_ID}-seed-{seed_tag}-eval-{evaluator_tag}-cohort-{cohort_tag}"


def score_submission(submission: Submission, sealed_seed: str, store: EvaluationStore,
                     work_root: str | Path, suite_id: str | None = None,
                     fresh: bool = False) -> dict:
    """Run a commit over a deterministic sealed suite and save only aggregates.

    All dataset generation and truth handling happens in this trusted process.
    Each container receives one input dataset, the immutable code snapshot, and
    one empty output directory. Per-run truth and results are deleted after the
    aggregate has been calculated.
    """
    if not sealed_seed:
        raise ValueError("Sealed seed is not configured")
    if suite_id is None:
        suite_id = make_suite_id(sealed_seed)
    store.set_active_suite(suite_id)
    cached = None if fresh else store.cached_result(submission.repository, submission.sha, suite_id)
    if cached is not None:
        store.record(submission.team, submission.repository, submission.sha, suite_id, "complete", cached)
        return {"cached": True, "summary": cached}
    store.record(submission.team, submission.repository, submission.sha, suite_id, "running")
    root = Path(work_root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="higgslab-hosted-", dir=root) as tmp:
            work = Path(tmp)
            snapshot = snapshot_commit(submission.repository, submission.sha, work / "snapshot")
            results, truths, valid_truths, valid_baseline = [], [], [], []
            started = time.monotonic()
            from higgslab.data import generate_dataset
            from higgslab.pipeline import run as run_baseline
            from higgslab.contract import validate_result

            baseline_results = []
            for idx, (seed, mu, beta) in enumerate(make_sealed_suite(sealed_seed)):
                pair = work / f"case-{idx}"
                data_dir, output_dir = pair / "data", pair / "output"
                baseline_output = pair / "baseline"
                data_dir.mkdir(parents=True)
                output_dir.mkdir()
                truth = generate_dataset(data_dir, seed=seed, mu=mu, beta=beta)
                truths.append(float(truth["mu"]))
                base_result = run_baseline(data_dir, baseline_output)
                baseline_results.append(base_result)
                remaining = MAX_SUBMISSION_WALL_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    continue
                try:
                    run_in_docker(snapshot, data_dir, output_dir,
                                  timeout_seconds=max(1, min(600, int(remaining))))
                except SandboxError:
                    # A failed case contributes to recovery failure, with no stdout/stderr retained.
                    continue
                try:
                    result_path = output_dir / "RESULT.json"
                    results.append(validate_result(result_path))
                    valid_truths.append(float(truth["mu"]))
                    valid_baseline.append(base_result)
                except (OSError, ValueError):
                    # A failed case contributes to recovery failure, with no stdout/stderr retained.
                    continue
            summary = summarize(results, valid_truths, baseline_results=valid_baseline,
                                total_cases=SUITE_SIZE)
            store.set_baseline(summarize(baseline_results, truths, baseline_results=baseline_results,
                                         total_cases=SUITE_SIZE), suite_id=suite_id)
        if summary["n"] == 0:
            store.record(submission.team, submission.repository, submission.sha, suite_id,
                         "failed", summary, error="No valid result across the sealed suite")
            return {"cached": False, "status": "failed", "summary": summary}
        store.record(submission.team, submission.repository, submission.sha, suite_id, "complete", summary)
        return {"cached": False, "summary": summary}
    except Exception as exc:
        # Public status receives a short classified message, never raw execution output or paths.
        reason = exc if isinstance(exc, (SandboxError, ValueError)) else RuntimeError("Scoring failed")
        store.record(submission.team, submission.repository, submission.sha, suite_id,
                     "failed", error=str(reason))
        raise


def score_final(sealed_seed: str, store: EvaluationStore, work_root: str | Path) -> list[dict]:
    """Freshly re-score latest parseable commit per team on the same secret suite."""
    if not sealed_seed:
        raise ValueError("Sealed seed is not configured")
    suite_id = make_suite_id(sealed_seed)
    store.set_active_suite(suite_id)
    final = []
    for row in store.latest_submissions():
        sub = Submission(row["team"], row["repository"], row["sha"])
        try:
            final.append(score_submission(sub, sealed_seed, store, work_root, suite_id=suite_id, fresh=True))
        except Exception:
            # Continue the final cohort pass; the per-team attempt already has a short failed status.
            final.append({"team": row["team"], "status": "failed"})
    return final
