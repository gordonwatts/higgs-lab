# Supervised classifier path

The supervised path learns to distinguish toy signal and background events from labeled training examples. The classifier score can become an input to the same template fit used by the rest of the tutorial.

## Train a portable model

```bash
uv run higgslab train datasets/public output/classifier.json --mode classifier --epochs 4
uv run higgslab run datasets/public output/classifier-result --model output/classifier.json
```

The exported JSON carries inference weights and preprocessing. The commands above test it through the shared reference pipeline. To have the executable submission use the model, train it directly to `submission/model.json`; `submission/analysis.py` detects that sidecar and routes to the common model pipeline. Then run `uv run higgslab check` and `uv run higgslab score-local --submission submission --output output/classifier-suite --count 12 --seed 71`. The implementation uses fixed train/validation/template partitions; fit scalers and train model parameters from partition 0 only. Keep labels, weights, event IDs, and partition identifiers out of model features.

## Exercise: one feature change

Start from the list in `higgslab.features.engineered`. Add one feature with a clear physical or statistical motivation, then ensure the executable submission uses it. Before running, predict whether it will change validation separation, template behavior, or both. Re-run the same checks and generated suite. Report the AUC if available, along with μ bias, average uncertainty, recovery slope, pull width, and failure rate.

Try a contrasting experiment: change a classifier setting in a way that improves AUC, then test whether the μ result improves. A good explanation distinguishes classifier ranking quality from measurement precision and calibration.

## Questions to answer

- Which information enters the classifier, and which fields are metadata?
- Was preprocessing learned from training events only?
- Are validation and template events independent from training?
- Did the fit use score bins with enough expected events?
- Did average uncertainty improve while pull width remained calibrated?

For an encoder representation instead of engineered features, see [MiniHEP](encoder.md). For the shared statistical objective, see [the fit](fit.md).
