# Statistical fit: from scores to μ

The fit turns event counts into an estimate of the signal strength μ. It compares binned observations with predicted background and signal yields. A simple conceptual form for bin *i* is:

```text
expected_i(μ, β) = μ × signal_i + β × background_i
```

Here β is a background normalization parameter. The likelihood describes the probability of observing the bin counts given expected yields and nuisance parameters. The fit finds the values most compatible with the data and estimates uncertainty from the likelihood shape. The provided code is the source of the exact implementation; this equation is a teaching sketch, not a complete statistical specification.

## Start from observables

The baseline uses a small set of kinematic observables and templates. An advanced classifier can replace or augment these with a score. This creates a bridge between machine learning and inference: the classifier orders events, while the fit accounts for expected yields and counting uncertainty.

The starter uses a 5 × 4 `(mT, mℓℓ)` binning and a half-typical-MC-event pseudocount in each template bin. This small regularization reduces empty or unstable bins when the teaching simulation is finite. It is an approximate teaching choice, not a full Barlow–Beeston treatment of template statistical uncertainty and not a detector-systematic model. The binning and pseudocount both matter to fit behavior, so record them when comparing variants.

Try these exercises one at a time:

- Compare a classifier-score template to the baseline kinematic variables.
- Change the number or placement of bins and track empty or low-yield bins. Compare the 5 × 4 starter binning with a coarser score binning while keeping the fit and sample fixed.
- Vary the half-event template pseudocount as a controlled regularization study; explain how finite-template uncertainty is approximated and what the pseudocount does not cover.
- Study how fixing or constraining β affects μ and its uncertainty.
- Compare μ recovery over generated samples with several injected μ values.
- As an advanced extension, scan the assumed Higgs mass; μ at the nominal mass remains the main scored result.

## Check uncertainty calibration

For each generated sample, a pull is `(fitted μ − injected μ) / reported uncertainty`. Across many samples, a well-calibrated uncertainty should yield a pull distribution with a width near one, subject to the limits of the toy model and suite size. Also inspect the fitted-versus-injected recovery slope: a value far from one or a large intercept can expose bias even when a single result looks plausible.

Run `uv run higgslab score-local --submission submission --output output/suite --count 12 --seed 71` to examine aggregate metrics from your executable submission. The suite results test the implementation on synthetic teaching data; they do not validate a real experimental analysis. To compare with the shared reference pipeline instead, omit `--submission`.
