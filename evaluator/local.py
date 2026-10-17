"""Local generated-suite scoring through the shared HiggsLab pipeline."""

from __future__ import annotations

from pathlib import Path
import tempfile

from .scoring import summarize
from .security import _copy_safe_tree, run_in_docker, SandboxError, MAX_RUNTIME_SECONDS


def score_local(dataset_generator=None, runner=None, suite_dir=None,
                seeds=(1401, 1402, 1403, 1404, 1405, 1406),
                mu_values=(0.0, 1.0, 1.5, 0.0, 1.0, 1.5), beta=1.0):
    """Run a local implementation over deterministic known-truth toy datasets.

    The optional callables make this useful to course authors and fixtures too.
    The default imports the public higgslab interfaces lazily.
    """
    if dataset_generator is None:
        from higgslab.data import generate_dataset
        dataset_generator = generate_dataset
    if runner is None:
        from higgslab.pipeline import run
        from higgslab.contract import validate_result

        def runner(dataset, output):
            run(dataset, output)
            return validate_result(output / "RESULT.json")

    if suite_dir is None:
        tmp = tempfile.TemporaryDirectory(prefix="higgslab-local-")
        suite_path = Path(tmp.name)
    else:
        tmp = None
        suite_path = Path(suite_dir)
    try:
        results, truths = [], []
        with tempfile.TemporaryDirectory(prefix="suite-", dir=suite_path) as work:
            root = Path(work)
            for i, (seed, mu) in enumerate(zip(seeds, mu_values)):
                data, output = root / f"{i}" / "data", root / f"{i}" / "output"
                data.mkdir(parents=True)
                output.mkdir()
                truth = dataset_generator(data, seed=seed, mu=mu, beta=beta)
                results.append(runner(data, output))
                truths.append(float(truth if isinstance(truth, (int, float)) else truth["mu"]))
        return summarize(results, truths)
    finally:
        if tmp is not None:
            tmp.cleanup()


def score_local_submission(submission_dir, *, suite_dir=None,
                           seeds=(1401, 1402, 1403, 1404, 1405, 1406),
                           mu_values=(0.0, 1.0, 1.5, 0.0, 1.0, 1.5), beta=1.0,
                           timeout_seconds=MAX_RUNTIME_SECONDS):
    """Score a local submission directory against a small public, known-truth suite."""
    from higgslab.data import generate_dataset
    from higgslab.pipeline import run as run_baseline
    from higgslab.contract import validate_result

    source = Path(submission_dir).resolve()
    if not source.is_dir() or source.is_symlink():
        raise ValueError("Submission path must be a regular directory")
    if len(seeds) != len(mu_values) or not seeds:
        raise ValueError("Local seeds and mu values must be nonempty and equally sized")
    temporary_root = Path(suite_dir) if suite_dir is not None else None
    if temporary_root is not None:
        temporary_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="higgslab-local-submission-",
                                     dir=temporary_root) as temporary:
        root = Path(temporary)
        snapshot = root / "snapshot"
        snapshot.mkdir()
        _copy_safe_tree(source, snapshot)
        results, truths, baselines = [], [], []
        for index, (seed, mu) in enumerate(zip(seeds, mu_values)):
            case = root / f"case-{index}"
            data, output, baseline_output = case / "data", case / "output", case / "baseline"
            data.mkdir(parents=True); output.mkdir(); baseline_output.mkdir()
            truth = generate_dataset(data, seed=int(seed), mu=float(mu), beta=float(beta))
            baseline = run_baseline(data, baseline_output)
            try:
                run_in_docker(snapshot, data, output, timeout_seconds=timeout_seconds)
                result = validate_result(output / "RESULT.json")
                results.append(result)
                baselines.append(baseline)
                truths.append(float(truth["mu"]))
            except (SandboxError, OSError, ValueError):
                continue
        return summarize(results, truths, baseline_results=baselines,
                         total_cases=len(seeds))
