# Quickstart

In about 10–15 minutes, install HiggsLab, run its baseline, inspect a result, and change one small component. The command-line pipeline is the submission source of truth. The optional exploration notebook lives at `notebooks/01-explore.ipynb` for looking at the data and output.

## 1. Install

Install Python 3.12 and [`uv`](https://docs.astral.sh/uv/), then clone your workshop repository and enter its folder. In a template checkout, run:

```bash
uv sync --extra ml --extra dev
```

This prepares the core numerical stack, optional PyTorch teaching paths, and development tools. CPU execution is supported; you do not need a GPU or an API key.

## 2. Run the baseline

```bash
uv run higgslab run datasets/public output
```

This runs the bundled baseline over the public sample and writes `output/RESULT.json`. The μ result is an estimate from a teaching dataset; do not interpret it as an ATLAS measurement.

### Read your first result

The current public baseline produces the following `submission-v1` result (shown rounded for readability). Numbers can change with the sample, fit settings, or model; read your own file when comparing runs.

```json
{
  "pois": [{"name": "mu", "value": 1.03426499, "stat": 0.09273447, "syst": 0.06214195, "total": 0.11163021}],
  "significance_obs": 10.7632,
  "discovery": true,
  "nuisances": {"hww_bkg_norm": {"value": 1.0012, "unc": 0.0315}},
  "interval_mu": [0.9241, 1.1473],
  "schema": "submission-v1"
}
```

`pois` contains the parameter of interest: `mu` is the signal yield relative to the nominal signal prediction. Here the estimate is about 1.03 times that prediction, with total uncertainty about 0.11. `interval_mu` gives the endpoints obtained by profiling the likelihood; `total` is half their separation. The fit splits that uncertainty into a counting component (`stat`) and a component associated with the background normalization constraint (`syst`); this is a teaching approximation, not a full inventory of experimental systematics.

`hww_bkg_norm` is the fitted background multiplier and its estimated uncertainty. `significance_obs` compares the fitted signal with the no-signal hypothesis in this model; `discovery` records whether it reaches the code's five-sigma threshold. A large value here describes this synthetic sample under its assumed model. It does not establish a real-world discovery or show that the uncertainty is reliable across repeated samples. See [how to read measurement evidence](ablation.md#how-to-read-the-results).

### Which command uses your edit?

All commands below are run with `uv run` from the repository root.

| Command | What it runs | Where to look |
| --- | --- | --- |
| `higgslab run datasets/public output` | Shared reference pipeline | `output/RESULT.json`; edits to `submission/analysis.py` have no effect here |
| `python submission/analysis.py datasets/public output/changed` | Editable submission on one sample | `output/changed/RESULT.json` |
| `higgslab check` | Dataset checks, reference runs, and two runs of the editable submission | Terminal PASS or diagnostic; submission files under `output/check/submission/` |
| `higgslab score-local --submission submission --output output/changed-suite --count 12 --seed 71` | Editable submission on repeated generated samples with known truth | `output/changed-suite/metrics.json` and `diagnostics.png` |

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

**Predict:** before editing, write down what a looser background constraint might do. Allowing the background multiplier to move more can let background explain counts that otherwise constrain μ, so the reported μ uncertainty may grow and the estimate may shift. This edit is an experiment; it is not expected to improve the result.

Now open `submission/analysis.py`. Change only the fit's `background_unc=.10` to `.15`. This experiment assumes the starter has no `submission/model.json`, whose model path bypasses this fit call. **Observe:** run the edited starter on the public sample, check reproducibility, then score it on the same generated suite seed:

```bash
uv run python submission/analysis.py datasets/public output/changed
uv run higgslab check
uv run higgslab score-local --submission submission --output output/changed-suite --count 12 --seed 71
```

Compare the single-sample μ and `total` uncertainty with the first result above, then compare `output/baseline-suite/metrics.json` and `output/changed-suite/metrics.json`. Since both suites use the same count and seed, they test your code change against the same generated cases.

### Read the suite metrics

`metrics.json` uses the `score-v1` schema. This excerpt comes from the unedited starter with the 12-case, seed-71 command above, rounded for readability; values will vary with your implementation and suite:

```json
{
  "schema": "score-v1",
  "count": 12,
  "failures": 0,
  "recovery": 1.0,
  "bias": 0.0345,
  "slope": 0.9930,
  "pull_width": 0.9089,
  "precision_rms": 0.1060,
  "mean_uncertainty": 0.1156,
  "false_discovery_rate": 0.0
}
```

| Field | What to inspect |
| --- | --- |
| `failures`, `recovery` | How many cases failed and the fraction producing valid results. Check these before comparing precision. Here `recovery` means successful execution, not the fitted-versus-injected slope. |
| `bias` | Average fitted minus injected μ; near zero means no average offset on these cases. |
| `slope` | Fitted-versus-injected μ slope; near one means the estimate tracks changes in signal strength. |
| `precision_rms` | Typical size of the μ error, including bias; smaller is useful alongside reliable uncertainties. |
| `mean_uncertainty` | Average reported μ uncertainty. Shrinking this alone does not make the estimate more accurate. |
| `pull_width` | Spread of error divided by reported uncertainty; near one is the calibration target. Above one suggests understated uncertainties or unmodeled variation; below one suggests overly broad uncertainties or other model effects. |
| `false_discovery_rate` | Fraction of successful no-signal cases flagged as discoveries. Zero in a small suite says little about rare false discoveries. |

The local suite computes bias, slope, RMS error, and pull diagnostics over successful positive-signal cases; the false-discovery fraction uses successful zero-signal cases. Twelve cases are a quick diagnostic, not precise calibration evidence. See the [fit guide](fit.md#check-uncertainty-calibration) for repeated-sample interpretation and limitations.

**Explain:** did the weaker constraint shift μ or enlarge its uncertainty as predicted? Did the suite's actual errors and pull width change consistently with that uncertainty? A wider interval can be more honest without reducing RMS error. If changes are tiny, report that too; these data may already constrain the background strongly. Record the prediction, observed numbers, and an explanation before changing another component.

Try other seams from the [analysis map](analysis.md), but make changes in the executable submission or copy a completed implementation into it; editing `student/components.py` alone does not change what the submission runs.

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
