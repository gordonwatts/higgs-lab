"""Short low-label core and optional matched transformer control (CPU)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
from scipy.stats import rankdata

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

from evaluator.scoring import summarize
from higgslab.data import generate_dataset
from higgslab.pipeline import run
from higgslab.training import _events, _load_pool, score, train


def reproduce(dataset, output, checkpoint, *, fraction=0.1, count=None,
              subset_seed=42, epochs=4, suite_size=6, transformer_control=False):
    if suite_size < 3:
        raise ValueError("suite size must be at least 3 to cover the truth grid")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    pool = _load_pool(dataset)
    val = np.flatnonzero(pool["partition"] == 1)
    events = _events(pool, val)
    modes = ["classifier", "frozen"] + (["scratch", "finetuned"] if transformer_control else [])
    models, report = {}, {}
    for mode in modes:
        start = time.perf_counter()
        path = train(dataset, output / f"{mode}.json", mode, epochs,
                     label_fraction=fraction, label_count=count, subset_seed=subset_seed,
                     checkpoint=checkpoint if mode != "classifier" else None)
        elapsed = time.perf_counter() - start
        payload = json.loads(path.read_text(encoding="utf-8"))
        models[mode] = path
        predictions = score(events, path)
        labels = pool["label"][val].astype(bool)
        positives, negatives = int(labels.sum()), int((~labels).sum())
        if not positives or not negatives:
            raise ValueError("validation partition must contain both classes for AUC")
        ranks = rankdata(predictions)
        auc = (ranks[labels].sum() - positives * (positives + 1) / 2) / (positives * negatives)
        report[mode] = {"validation_auc": float(auc), "label_budget": payload["label_budget"],
                        "architecture": payload.get("architecture", "engineered-feature-MLP"),
                        "scaler": payload["scaler"], "checkpoint": payload.get("checkpoint"),
                        "adaptation_compute": {"epochs": epochs, "batch_size": 128,
                            "optimizer_steps": epochs * int(np.ceil(payload["label_budget"]["count"] / 128)),
                            "elapsed_seconds_including_io": elapsed},
                        "classification": payload["classification"]}
    assert all(value["label_budget"] == report["classifier"]["label_budget"] for value in report.values())
    truths = [float([0, 1, 1.5][i % 3]) for i in range(suite_size)]
    baseline, results = [], {mode: [] for mode in modes}
    for i, truth in enumerate(truths):
        case = output / "suite" / f"case-{i}"
        generate_dataset(case, seed=710 + i, mu=truth, beta=1.0)
        baseline.append(run(case, output / "fits" / f"{i}-baseline"))
        for mode, model in models.items():
            results[mode].append(run(case, output / "fits" / f"{i}-{mode}", model_path=model))
    for mode in modes:
        report[mode]["metrics"] = summarize(results[mode], truths, baseline_results=baseline)
    result = {"schema": "low-label-v1", "dataset": str(dataset),
              "pool_sha256": hashlib.sha256((Path(dataset) / "mc/pool.npz").read_bytes()).hexdigest(),
              "checkpoint_sha256": hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
              "seed": 42, "subset_seed": subset_seed,
              "partitions": {"unlabeled_pretraining": 0, "labeled_training": 0, "validation": 1, "templates": 2},
              "suite": {"seeds": list(range(710, 710 + suite_size)), "truths": truths,
                        "beta": 1.0, "score_bins": 8},
              "interpretation": "Small synthetic sample only. AUC does not guarantee mu precision or calibration. Matching adaptation epochs does not match total compute; checkpoint pretraining is additional.",
              "models": report}
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="datasets/public")
    parser.add_argument("--output", default="output/low-label")
    parser.add_argument("--checkpoint", default="solutions/models/encoder.json")
    budget = parser.add_mutually_exclusive_group()
    budget.add_argument("--label-fraction", type=float, default=0.1)
    budget.add_argument("--label-count", type=int)
    parser.add_argument("--subset-seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--suite-size", type=int, default=6)
    parser.add_argument("--transformer-control", action="store_true")
    args = parser.parse_args()
    reproduce(args.dataset, args.output, args.checkpoint, fraction=args.label_fraction,
              count=args.label_count, subset_seed=args.subset_seed, epochs=args.epochs,
              suite_size=args.suite_size, transformer_control=args.transformer_control)
    print(Path(args.output) / "report.json")
