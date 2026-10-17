"""Rehearse the four student inference paths in the real restricted container.

Run only after building ``evaluator/Dockerfile`` as the configured sandbox image:

    uv run python scripts/verify_container_paths.py --count 12

This trusted harness creates the synthetic inputs outside the container, mounts
them read-only through ``run_in_docker``, and saves the public suite definition
and aggregate diagnostics. It does not use sealed data, fetch code, mount
credentials, or write truth into a dataset.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from evaluator.security import DOCKER_IMAGE, run_in_docker
from evaluator.scoring import summarize
from higgslab.contract import validate_result
from higgslab.data import generate_dataset


PATHS = {
    "starter": None,
    "classifier": ROOT / "solutions" / "models" / "classifier.json",
    "frozen": ROOT / "solutions" / "models" / "frozen.json",
    "finetuned": ROOT / "solutions" / "models" / "finetuned.json",
}
MU_VALUES = (0.0, 0.0, 0.0, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0)
BETA_VALUES = (0.8, 1.0, 1.2, 0.9, 1.1)


def prepare_snapshot(destination: str | Path, model_path: str | Path | None = None) -> Path:
    """Build the minimal immutable runner tree used by a student submission."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    source_submission = ROOT / "submission"
    for name in ("analysis.py", "run.sh"):
        source = source_submission / name
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(f"required regular file is missing: submission/{name}")
        shutil.copyfile(source, destination / name)
    if model_path is not None:
        model_path = Path(model_path)
        if not model_path.is_file() or model_path.is_symlink():
            raise FileNotFoundError(f"reference model is missing: {model_path.name}")
        shutil.copyfile(model_path, destination / "model.json")
    expected = {"analysis.py", "run.sh"} | ({"model.json"} if model_path is not None else set())
    actual = {path.name for path in destination.iterdir()}
    if actual != expected:
        raise RuntimeError("verification snapshot contains unexpected files")
    return destination


def suite_points(count: int, seed: int) -> list[tuple[int, float, float]]:
    """Return a reproducible mixed-truth suite with nulls and varied background."""
    if count < 6:
        raise ValueError("count must be at least 6 to include null and signal cases")
    return [
        (seed + i * 97, MU_VALUES[i % len(MU_VALUES)], BETA_VALUES[i % len(BETA_VALUES)])
        for i in range(count)
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(output: str | Path, *, count: int = 12, seed: int = 761203) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "schema": "container-paths-verification-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "data_origin": "synthetic teaching surrogate; not ATLAS data",
        "suite": {"count": count, "seed": seed, "cases": []},
        "container": {"image": DOCKER_IMAGE, "paths": {}},
        "public_repeat": {"dataset": "datasets/public", "repetitions_per_path": 2, "paths": {}},
    }
    points = suite_points(count, seed)
    with tempfile.TemporaryDirectory(prefix="higgslab-container-check-", dir=output) as temp:
        temp_root = Path(temp)
        datasets: list[tuple[Path, float, float]] = []
        for index, (case_seed, mu, beta) in enumerate(points):
            dataset = temp_root / f"suite-{index:02d}"
            truth = generate_dataset(dataset, seed=case_seed, mu=mu, beta=beta)
            if (dataset / "truth.json").exists() or (dataset / "RESULT.json").exists():
                raise RuntimeError("truth or model result was written beside mounted input")
            datasets.append((dataset, float(truth["mu"]), float(truth["beta"])))
            report["suite"]["cases"].append({"index": index, "mu": mu, "beta": beta,
                                               "input_sha256": _sha256(dataset / "data" / "events.npz")})

        public_dataset = ROOT / "datasets" / "public"
        if not public_dataset.is_dir():
            raise FileNotFoundError("datasets/public is required for the deterministic repeat check")
        public_inputs = sorted(p for p in public_dataset.rglob("*") if p.is_file())
        public_hashes_before = {p.relative_to(public_dataset).as_posix(): _sha256(p) for p in public_inputs}

        for name, model in PATHS.items():
            print(f"Checking {name}: {count} suite cases and two repeat runs", flush=True)
            path_report = {"status": "running", "valid_cases": 0, "runtime_seconds": 0.0}
            report["container"]["paths"][name] = path_report
            started = time.monotonic()
            measured, truths = [], []
            try:
                snapshot = prepare_snapshot(temp_root / f"snapshot-{name}", model)
                for index, (dataset, mu, _beta) in enumerate(datasets):
                    result_dir = temp_root / f"result-{name}-{index:02d}"
                    run_in_docker(snapshot, dataset, result_dir)
                    result = validate_result(result_dir / "RESULT.json")
                    measured.append(result)
                    truths.append(mu)
                    if (index + 1) % 10 == 0:
                        print(f"  {name}: {index + 1}/{count} valid cases", flush=True)
                path_report["valid_cases"] = len(measured)
                path_report["summary"] = summarize(measured, truths, total_cases=count)

                repeat_hashes = []
                for repeat in range(2):
                    result_dir = temp_root / f"public-{name}-{repeat}"
                    run_in_docker(snapshot, public_dataset, result_dir)
                    result_path = result_dir / "RESULT.json"
                    validate_result(result_path)
                    repeat_hashes.append(_sha256(result_path))
                path_report["public_repeat"] = {
                    "deterministic": repeat_hashes[0] == repeat_hashes[1],
                    "result_sha256": repeat_hashes,
                }
                path_report["status"] = "passed" if path_report["public_repeat"]["deterministic"] else "failed"
                if path_report["status"] == "failed":
                    path_report["error"] = "Repeated public input produced different result bytes"
            except Exception as exc:
                path_report["status"] = "failed"
                path_report["error"] = f"{type(exc).__name__}: {exc}"[:300]
            finally:
                path_report["runtime_seconds"] = round(time.monotonic() - started, 3)
                print(f"  {name}: {path_report['status']}", flush=True)

        public_hashes_after = {p.relative_to(public_dataset).as_posix(): _sha256(p)
                               for p in public_dataset.rglob("*") if p.is_file()}
        report["public_repeat"]["input_unchanged"] = public_hashes_before == public_hashes_after
    failures = [name for name, row in report["container"]["paths"].items() if row["status"] != "passed"]
    if not report["public_repeat"]["input_unchanged"]:
        failures.append("public-input-mutated")
    report["status"] = "passed" if not failures else "failed"
    if failures:
        report["failures"] = failures
    report_path = output / "docker-paths-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
                           encoding="utf-8", newline="\n")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output")
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--seed", type=int, default=761203)
    args = parser.parse_args(argv)
    result = verify(args.output, count=args.count, seed=args.seed)
    print(json.dumps({"status": result["status"], "report": str(args.output / "docker-paths-report.json"),
                      "paths": {name: item["status"] for name, item in result["container"]["paths"].items()}},
                     indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
