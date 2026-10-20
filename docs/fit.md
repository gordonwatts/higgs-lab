# Statistical fit: from scores to μ

The fit turns event counts into an estimate of the signal strength μ. It compares binned observations with predicted background and signal yields. A simple conceptual form for bin *i* is:

```text
expected_i(μ, β) = μ × signal_i + β × background_i
```

Here β is a background normalization parameter. The likelihood describes the probability of observing the bin counts given expected yields and nuisance parameters. The fit finds the values most compatible with the data and estimates uncertainty from the likelihood shape. The provided code is the source of the exact implementation; this equation is a teaching sketch, not a complete statistical specification.

## Start from observables

The baseline uses a small set of kinematic observables and templates. An advanced classifier can replace or augment these with a score. This creates a bridge between machine learning and inference: the classifier orders events, while the fit accounts for expected yields and counting uncertainty.

For a measurement, good event ranking is a means to an end: recover the signal yield with an uncertainty that describes how wrong the estimate could be. The [model comparison](ablation.md#how-to-read-the-results) walks through an example where a high-AUC classifier gives a weak measurement after its scores are collapsed into a single bin.

Try these exercises one at a time:

- Compare a classifier-score template to the baseline kinematic variables.
- Change the number or placement of bins and track empty or low-yield bins. Compare the 5 × 4 starter binning with a coarser score binning while keeping the fit and sample fixed.
- Vary the half-event template pseudocount as a controlled regularization study; explain how finite-template uncertainty is approximated and what the pseudocount does not cover.
- Study how fixing or constraining β affects μ and its uncertainty.
- Compare μ recovery over generated samples with several injected μ values.
- As an advanced extension, scan the assumed Higgs mass; μ at the nominal mass remains the main scored result.

## Check uncertainty calibration

For each generated sample, a pull is `(fitted μ − injected μ) / reported uncertainty`. Across many samples, a well-calibrated uncertainty should yield a pull distribution with a width near one, subject to the limits of the toy model and suite size. Also inspect the fitted-versus-injected recovery slope: a value far from one or a large intercept can expose bias even when a single result looks plausible.

Known injected μ makes these checks possible: we can compare the answer with truth repeatedly, rather than judging one attractive estimate. Bias asks whether the method systematically overshoots or undershoots; RMS residual measures the typical error, including that bias. Compare both with mean reported uncertainty. Narrower uncertainty with unchanged or larger actual errors can make a conclusion less trustworthy. A pull width above one suggests that errors vary more than the quoted uncertainties allow; a width below one can indicate overly broad uncertainties. Also inspect pull mean (target zero), failures, and recovery at different injected μ values, since a width near one alone does not rule out a systematic offset.

Pull width is a useful calibration diagnostic, not a direct measurement of interval coverage (the fraction of intervals containing truth). Small suites make all these estimates noisy. Zero discoveries in a handful of no-signal cases cannot test a very rare false-discovery probability. Larger suites can strengthen checks within this generator's assumptions, but cannot test detector effects or mismodeling absent from the synthetic data.

Run `uv run higgslab score-local --submission submission --output output/suite --count 12 --seed 71` to examine aggregate metrics from your executable submission. The suite results test the implementation on synthetic teaching data; they do not validate a real experimental analysis. To compare with the shared reference pipeline instead, omit `--submission`.

## Advanced: finite simulation and template regularization

The starter uses a 5 × 4 `(mT, mℓℓ)` binning and a half-typical-MC-event pseudocount in each template bin. A pseudocount adds a small artificial yield to stabilize empty or sparse bins; here its size is set from the typical simulated event weight. This regularization changes the fit and should be recorded along with the binning.

Finite simulation also means predicted bin yields are uncertain. Barlow–Beeston methods explicitly represent template statistical uncertainty with additional likelihood parameters. The starter's pseudocount is an approximate teaching choice, not that full treatment and not a model of detector systematics. Try the regularization exercise after understanding the recovery and calibration checks above.
