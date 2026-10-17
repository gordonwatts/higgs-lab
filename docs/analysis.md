# Analysis map

The common pipeline makes it possible to change one stage at a time and still reach a comparable measurement.

```text
event records → features or event encoder → event score → templates → likelihood fit → RESULT.json
```

The starter provides a working baseline. Your task is to understand one boundary and improve it with evidence.

| Stage | What it does | A focused experiment |
| --- | --- | --- |
| Load | Reads and validates event fields and weights. | Check one field's units, shape, and missing-object convention. |
| Features / encoder | Converts raw event fields to a model representation. | Add a physically motivated variable or compare token embeddings. |
| Score | Estimates how signal-like each event is. | Compare the score to a simple baseline; inspect validation behavior. |
| Templates | Groups events into bins and predicts signal/background yields. | Change one observable, bin edge, or score binning. |
| Fit | Estimates μ and its uncertainty from observed counts. | Compare fit variables or a background constraint. |
| Result | Serializes a portable measurement for validation. | Confirm the result is finite and meets the shared contract. |

## What counts as an improvement?

Record the baseline μ and uncertainty, run the same generated suite before and after a change, and inspect bias, recovery slope, pull width, average precision, false discoveries, and failures. The local suite contains known truth for the process but reports aggregate diagnostics. It is designed to make repeated-sample behavior visible.

Classifier AUC and masked-reconstruction loss are diagnostics, not the shared outcome. A better AUC can produce a worse measurement if the score does not separate the relevant yields in a stable way, if templates are poorly populated, or if the fitted uncertainties are miscalibrated. Explain both what changed and what evidence supports your conclusion.

## Suggested checkpoints

1. Run `uv run higgslab run datasets/public output/reference` to save the shared reference pipeline result.
2. Run `uv run higgslab score-local --submission submission --output output/before --count 12 --seed 71` to record the editable submission's baseline.
3. Inspect the schema and change exactly one stage in the executable `submission/analysis.py`; predict what should move.
4. Run `uv run higgslab check` and score again with the same `--count` and `--seed` into a new output folder.
5. Compare both measurement behavior and the diagnostic closest to your change.
6. Keep the change only if the evidence and tradeoffs make sense; a clear negative result is a good report.

The separate `student/components.py` file shows feature, template, and measurement seams for reference. It does not run automatically. Copy your chosen implementation into the submission path before comparing it with `score-local --submission` or turning it in.

Choose a [classifier](classifier.md), [encoder](encoder.md), or [fit](fit.md) exercise. The optional [agent guide](agents.md) offers prompts for students who want an assistant to help inspect or implement one component.
