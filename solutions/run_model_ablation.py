"""Reproduce the checked-in CPU model/fit comparison on generated toy suites."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

REPOSITORY = Path(__file__).parents[1]
sys.path.insert(0, str(REPOSITORY))
_matplotlib_config = REPOSITORY / "output" / ".matplotlib"
_matplotlib_config.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_matplotlib_config))

import numpy as np
from scipy.stats import rankdata
import matplotlib.pyplot as plt

from evaluator.scoring import summarize
from higgslab.data import generate_dataset, load_dataset
from higgslab.pipeline import run
from higgslab.training import score, train


def _auc(labels, scores):
    labels = np.asarray(labels, dtype=bool)
    ranks = rankdata(np.asarray(scores), method="average")
    positives, negatives = int(labels.sum()), int((~labels).sum())
    if positives == 0 or negatives == 0:
        return None
    return float((ranks[labels].sum() - positives * (positives + 1) / 2) /
                 (positives * negatives))


def reproduce(output_dir: str | Path, suite_size: int = 12):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="higgslab-ablation-", dir=output_dir) as temp:
        root = Path(temp)
        training_data = root / "training"
        generate_dataset(training_data, seed=42, mu=1.0, beta=1.0)
        _, pool, meta = load_dataset(training_data)
        partition = pool["partition"]
        val = partition == 1
        model_paths = {}
        validation_auc = {}
        validation_scores = {}
        model_payloads = {}
        pool_events = {key: value for key, value in pool.items()
                       if key not in {"label", "weight", "process", "event_id", "partition"}}
        for mode in ("classifier", "frozen", "finetuned"):
            path = output_dir / f"{mode}.json"
            train(training_data, path, mode, epochs=4)
            model_paths[mode] = path
            model_payloads[mode] = json.loads(path.read_text(encoding="utf-8"))
            validation_scores[mode] = score(
                {key: value[val] for key, value in pool_events.items()}, path)
            validation_auc[mode] = _auc(pool["label"][val], validation_scores[mode])

        seeds = list(range(710, 710 + suite_size))
        truth_grid = [0.0, 1.0, 1.5]
        truths = [truth_grid[i % len(truth_grid)] for i in range(suite_size)]
        results: dict[str, list[dict]] = {key: [] for key in
                                          ("template-fit", "classifier", "frozen", "finetuned",
                                           "classifier-4-score-bins", "classifier-1-score-bin")}
        for i, (seed, mu) in enumerate(zip(seeds, truths)):
            dataset = root / f"suite-{i}"
            result_dir = root / f"result-{i}"
            generate_dataset(dataset, seed=seed, mu=mu, beta=1.0)
            results["template-fit"].append(run(dataset, result_dir / "template"))
            for mode, model_path in model_paths.items():
                results[mode].append(run(dataset, result_dir / mode, model_path=model_path))
            results["classifier-4-score-bins"].append(run(
                dataset, result_dir / "classifier-4-score-bins", model_path=model_paths["classifier"],
                bins=[np.linspace(0.0, 1.0, 5)]))
            results["classifier-1-score-bin"].append(run(
                dataset, result_dir / "classifier-1-score-bin", model_path=model_paths["classifier"],
                bins=[np.linspace(0.0, 1.0, 2)]))

        model_metrics = {}
        for key, values in results.items():
            if key == "template-fit":
                auc, fit_bins = None, "(mT, mll): 5 x 4"
            elif key in ("classifier-1-score-bin", "classifier-4-score-bins"):
                auc, fit_bins = validation_auc["classifier"], 4
                fit_bins = 1 if key == "classifier-1-score-bin" else fit_bins
            else:
                auc, fit_bins = validation_auc[key], 8
            model_metrics[key] = {
                "validation_auc": auc,
                "fit_bins": fit_bins,
                "parameter_count": (None if key == "template-fit" else
                                    model_payloads["classifier" if key in ("classifier-1-score-bin", "classifier-4-score-bins") else key]["parameter_count"]),
                "pretraining": (model_payloads[key]["pretraining"]
                                if key in ("frozen", "finetuned") else None),
                "classification": (model_payloads["classifier" if key in ("classifier-1-score-bin", "classifier-4-score-bins") else key]["classification"]
                                   if key != "template-fit" else None),
                "metrics": summarize(values, truths,
                                     baseline_results=results["template-fit"]),
            }
        pool_hash = hashlib.sha256((training_data / "mc" / "pool.npz").read_bytes()).hexdigest()
        report = {
            "schema": "model-ablation-v1",
            "provenance": {
                "dataset_origin": meta["origin"],
                "training_seed": 42,
                "training_pool_size": len(pool["label"]),
                "training_pool_sha256": pool_hash,
                "epochs": 4,
                "suite_size": suite_size,
                "suite_seed_start": seeds[0] if seeds else None,
                "suite_truth_grid": truth_grid,
                "suite_beta": 1.0,
                "template_partition": 2,
                "fit_settings": "shared higgslab.pipeline and likelihood; the (mT,mll) edges and nuisance prior stay fixed, while classifier score-bin counts vary only where listed",
            },
            "models": model_metrics,
        }
        _write_plots(pool["label"][val], validation_scores,
                     {key: value["pretraining"] for key, value in model_payloads.items()
                      if "pretraining" in value},
                     {key: value["classification"] for key, value in model_payloads.items()})
    destination = Path(__file__).parents[1] / "docs" / "assets" / "ablation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


def _write_plots(labels, scores, histories, classifier_histories):
    assets = Path(__file__).parents[1] / "docs" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    labels = np.asarray(labels, dtype=bool)
    fig, ax = plt.subplots(figsize=(6, 5))
    for mode, values in scores.items():
        order = np.argsort(-values)
        ordered_labels = labels[order]
        tpr = np.r_[0, np.cumsum(ordered_labels) / ordered_labels.sum()]
        fpr = np.r_[0, np.cumsum(~ordered_labels) / (~ordered_labels).sum()]
        ax.plot(fpr, tpr, label=f"{mode} (AUC { _auc(labels, values):.3f})")
    ax.plot([0, 1], [0, 1], color="0.6", linestyle="--")
    ax.set(xlabel="Background acceptance", ylabel="Signal acceptance", title="Validation ROC")
    ax.legend()
    fig.tight_layout()
    fig.savefig(assets / "model_roc.png", dpi=150)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(scores), figsize=(4 * len(scores), 3.5), sharey=True)
    for ax, (mode, values) in zip(axes, scores.items()):
        ax.hist(values[labels], bins=np.linspace(0, 1, 21), density=True,
                histtype="step", linewidth=1.8, label="signal")
        ax.hist(values[~labels], bins=np.linspace(0, 1, 21), density=True,
                histtype="step", linewidth=1.8, label="background")
        ax.set(title=mode, xlabel="Classifier score")
    axes[0].set_ylabel("Density")
    axes[-1].legend()
    fig.suptitle("Held-out validation score distributions")
    fig.tight_layout()
    fig.savefig(assets / "model_scores.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for mode, history in histories.items():
        epoch = np.arange(1, len(history["train_loss"]) + 1)
        ax.plot(epoch, history["train_loss"], marker="o", label=f"{mode} train")
        ax.plot(epoch, history["validation_loss"], marker="x", linestyle="--",
                label=f"{mode} validation")
    ax.set(xlabel="Pretraining epoch", ylabel="Masked four-vector MSE",
           title="MiniHEP masked reconstruction")
    ax.legend()
    fig.tight_layout()
    fig.savefig(assets / "pretraining_loss.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for mode, history in classifier_histories.items():
        epoch = np.arange(1, len(history["train_loss"]) + 1)
        ax.plot(epoch, history["train_loss"], marker="o", label=f"{mode} train")
        ax.plot(epoch, history["validation_loss"], marker="x", linestyle="--",
                label=f"{mode} validation")
    ax.set(xlabel="Classification epoch", ylabel="Weighted BCE loss",
           title="Train and held-out validation loss")
    ax.legend()
    fig.tight_layout()
    fig.savefig(assets / "classifier_loss.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="output/model-ablation")
    parser.add_argument("--suite-size", type=int, default=24)
    args = parser.parse_args()
    report = reproduce(args.output, args.suite_size)
    print(json.dumps({"file": "docs/assets/ablation.json", "models": report["models"]}, indent=2))
