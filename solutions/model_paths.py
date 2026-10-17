"""Reference commands for the three classifier paths in the student exercise.

The implementation is in ``higgslab.training`` so students can change one
model component while keeping the dataset splits and fit pipeline fixed.
Run from a checkout with the project environment activated.
"""

from pathlib import Path

from higgslab.training import score, train


def reference_run(dataset_dir: str | Path, output_dir: str | Path) -> dict[str, object]:
    output_dir = Path(output_dir)
    results = {}
    for mode in ("supervised", "minihep-frozen", "minihep-finetuned"):
        model_file = train(dataset_dir, output_dir / f"{mode}.json", mode=mode, epochs=4)
        results[mode] = model_file
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset_dir")
    parser.add_argument("output_dir")
    arguments = parser.parse_args()
    for path in reference_run(arguments.dataset_dir, arguments.output_dir).values():
        print(path)
