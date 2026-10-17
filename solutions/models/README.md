# Reference inference models

These three portable JSON models were trained from the fixed `dataset-v1`
simulation pool with seed 42 and four CPU epochs. `manifest.json` records the
training pool SHA-256 and each model's SHA-256, mode, epoch count, and parameter
count. The pool is a synthetic teaching surrogate, not ATLAS data.

Use them for the model comparisons without retraining. To make a self-contained
classifier submission, train or copy one model to `submission/model.json`; the
submission runner finds that file beside `analysis.py` and scores the data
through the shared pipeline.

```powershell
uv run python solutions/train_submission_model.py datasets/public --mode classifier
uv run python -m evaluator score-local
```

The encoder models are about 375 kB each and the direct classifier is about
53 kB. They contain only exported weights and train-only preprocessing
statistics; inference does not need the original training pool.
