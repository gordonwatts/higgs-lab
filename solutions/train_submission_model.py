"""Train a portable classifier directly into submission/model.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from higgslab.training import train


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="dataset-v1 directory")
    parser.add_argument("--mode", choices=("classifier", "frozen", "finetuned"),
                        default="classifier")
    parser.add_argument("--epochs", type=int, default=4)
    args = parser.parse_args()
    repository = Path(__file__).parents[1]
    model_path = repository / "submission" / "model.json"
    train(args.dataset, model_path, args.mode, args.epochs)
    print(f"Wrote portable model: {model_path.relative_to(repository)}")
