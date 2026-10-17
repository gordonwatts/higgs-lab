# Quickstart

In about 10–15 minutes, install HiggsLab, run its baseline, inspect a result, and change one small component. The command-line pipeline is the submission source of truth. The optional exploration notebook lives at `notebooks/01-explore.ipynb` for looking at the data and output.

## 1. Get your workshop copy

Start from the published workshop landing page your instructor shared. Open its **Workshop repository** link. On GitHub, use **Fork** to make a copy under your own account, then clone that fork and enter its folder:

```bash
git clone https://github.com/YOUR-USERNAME/WORKSHOP-REPOSITORY.git
cd WORKSHOP-REPOSITORY
```

Replace the placeholders with your GitHub username and the repository name shown on the landing page. Work from this repository's root folder. The fork is your copy for making and pushing changes; the instructor's workshop repository is the source to fork.

The repository link is filled in when an instructor configures and publishes a workshop. If you are reading a local preview or an unconfigured template checkout, its landing page will not show a cohort repository link. Ask your instructor for the published workshop landing-page URL before forking. If you already have a checkout from your instructor, use that checkout and continue below from its root.

Install Python 3.12 and [`uv`](https://docs.astral.sh/uv/), then install the project dependencies:

```bash
uv sync --extra ml --extra dev
```

This prepares the core numerical stack, optional PyTorch teaching paths, and development tools. CPU execution is supported; you do not need a GPU or an API key.

## 2. Run the baseline

```bash
uv run higgslab run datasets/public output
```

This runs the bundled baseline over the public sample and writes `output/RESULT.json`. The μ result is an estimate from a teaching dataset; do not interpret it as an ATLAS measurement.

`higgslab run` is the shared reference pipeline. The editable starter is `submission/analysis.py`, invoked locally by `submission/run.sh` (on Windows, `higgslab check` uses its equivalent Python entry point). A change in the submission folder will not alter the shared reference command.

```bash
uv run higgslab check
```

The check command validates the dataset and reference pipeline, then runs your submission twice to confirm it writes the same valid result both times. If it reports a failed check, copy the exact diagnostic into the [FAQ](faq.md) troubleshooting steps before changing code.

## 3. Change one thing

First record the submission's baseline on a fixed generated suite:

```bash
uv run higgslab score-local --submission submission --output output/baseline-suite --count 12 --seed 71
```

Now open `submission/analysis.py`. Change the fit's `background_unc=.10` to `.15` as one controlled experiment. Run the edited starter on the public sample, check reproducibility, then score it on the same generated suite seed:

```bash
uv run python submission/analysis.py datasets/public output/changed
uv run higgslab check
uv run higgslab score-local --submission submission --output output/changed-suite --count 12 --seed 71
```

Compare `output/baseline-suite/metrics.json` and `output/changed-suite/metrics.json`. The suite checks whether the edit affected bias, RMS residual, pull width, uncertainty, false discoveries, and failures. Since both runs use the same seed, the comparison isolates your code change. Try other seams from the [analysis map](analysis.md), but make changes in the executable submission or copy a completed implementation into it; editing `student/components.py` alone does not change what the submission runs.

To generate a known-truth local sample for an experiment:

```bash
uv run higgslab generate output/toy --seed 42 --mu 1
uv run higgslab run output/toy output/toy-result
```

To score the shared reference pipeline on repeated generated samples, use:

```bash
uv run higgslab score-local --output output/suite --count 12
```

This reports aggregate recovery and calibration diagnostics; it does not publish per-event truth. Preserve the generated files only if you need to inspect your own local experiment.

## 4. Optional model paths

Train one small model and pass its exported JSON to the shared pipeline:

```bash
uv run higgslab train datasets/public output/model.json --mode classifier --epochs 4
uv run higgslab run datasets/public output/classifier --model output/model.json
```

For the submission to use a trained model, save it as `submission/model.json`, then run `higgslab check` and `score-local --submission submission`. The other teaching modes are `frozen` and `finetuned`. See [classifier](classifier.md) and [encoder](encoder.md) for a fair comparison.

## Where to go next

Use the [physics bridge](physics.md) and [data page](data.md) if the event vocabulary is new. Use the [submission page](submission.md) when your chosen experiment is ready to share.
