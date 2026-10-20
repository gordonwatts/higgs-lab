# Model and fit comparison

This comparison uses the same synthetic event pool, four training epochs, held-out template partition, 24-case mixed-μ suite, and common fit settings for each path. It is a compact teaching demonstration, not an acceptance threshold or an experimental result.

!!! warning "Synthetic teaching sample"
    All results below use a synthetic teaching surrogate, not ATLAS data. The suite has only 24 cases, so differences are noisy and should be treated as preliminary. A zero false-discovery fraction in a small null sample is not a bound on rare false discoveries. Use 50 or more cases before making a strong claim.

## How to read the results

The physics question is whether these events support a signal, how much signal is present, and how much confidence to place in that estimate. The signal strength μ measures signal yield relative to the nominal prediction: μ = 0 means no signal and μ = 1 means the nominal signal yield. A classifier helps by ordering events from background-like to signal-like; the fit uses counts in that ordering to estimate μ and its uncertainty.

Read the table in three steps:

1. **Ranking:** validation AUC measures how well the model orders held-out signal and background events. About 0.5 means random ranking and 1 means perfect separation. A higher AUC can help a fit, but does not measure signal yield or validate its uncertainty.
2. **Measurement:** μ bias is the average fitted-minus-injected offset; RMS residual is the typical size of that error, including bias. Near-zero bias and small RMS residual are desirable. Mean μ uncertainty is what the fit claims about its precision. A smaller claimed uncertainty is useful only if actual errors support it.
3. **Reliability:** pull width compares the spread of errors with reported uncertainties; near one is the target, above one can signal overconfidence or missing variation, and below one can signal unnecessarily broad uncertainties or other model effects. Recovery slope tests whether fitted μ tracks injected μ; far from one indicates a distorted response. Check failed cases too: favorable averages among successful fits can hide a fragile method. False discovery rate asks how often no-signal cases pass the discovery threshold.

We repeat generated samples with known injected μ because one plausible fitted number cannot establish these properties. Repetition reveals systematic offsets, case-to-case errors, and whether stated uncertainty reflects those errors. The table uses a mixed-μ suite, so its aggregates can also conceal problems at a particular signal strength; inspect recovery across μ as well. Twelve or 24 cases give quick teaching diagnostics. Even 50 or more cases do not establish real-data validity or precisely measure a rare five-sigma false-discovery rate. See the [fit guide](fit.md#check-uncertainty-calibration) for definitions and the [Quickstart](setup.md#read-the-suite-metrics) for local JSON field names.

## Results

<div id="ablation-status" role="status" aria-live="polite">Loading the generated model comparison…</div>
<div id="ablation-table"></div>

The supervised classifier reaches validation AUC 0.8904. With eight score bins, its RMS μ residual is 0.0782, mean reported μ uncertainty is 0.0792, and pull width is 1.027. Keeping the same trained classifier and collapsing its score to one bin leaves AUC unchanged at 0.8904, but RMS residual rises to 0.1265, mean reported uncertainty to 0.474, pull width falls to 0.271, and discovery power is zero in this suite. The fit cannot use ranking information that has been discarded by the one-bin template. This controlled example demonstrates that classification quality alone does not determine measurement quality.

The four-score-bin version also keeps AUC at 0.8904; its RMS residual is 0.0779 and pull width is 1.023. Fine-tuned MiniHEP has AUC 0.8821, RMS residual 0.0798, and pull width 1.009. The frozen probe has lower AUC (0.6338) and a larger RMS residual (0.2927) and mean uncertainty (0.323). These are results from this one 24-case synthetic suite, not universal model comparisons.

The one-bin classifier has a higher AUC than fine-tuned MiniHEP, yet its much larger uncertainty makes a weaker measurement. It still estimates μ with a small average bias (0.0136), but its errors vary much less than its claimed uncertainty: pull width 0.271 is far below one. Collapsing all scores into one count removes the fit's ability to distinguish signal-like and background-like regions, so changes in background and signal become harder to separate. This is why good event ranking alone cannot support a strong measurement claim.

This comparison deliberately changes the downstream binning to expose the bottleneck; it does not establish that the classifier architecture is worse. Moving the same classifier from one bin to eight restores the fit's use of the score ordering. Four bins have a slightly lower RMS residual than eight (0.0779 versus 0.0782), but a slightly larger mean uncertainty (0.0823 versus 0.0792). Those small differences do not establish an optimal bin count in this 24-case suite; more bins need enough simulation events to populate their templates reliably.

## Diagnostic plots

![Validation ROC curves for the model paths.](assets/model_roc.png)

![Classifier score distributions for the model paths.](assets/model_scores.png)

![Training and validation masked-reconstruction losses for MiniHEP.](assets/pretraining_loss.png)

![Training and validation classification loss for the supervised and encoder paths.](assets/classifier_loss.png)

The four-epoch encoder is a small foundation-model teaching prototype. Its reconstruction and classification losses are diagnostics, not evidence by themselves of downstream measurement quality. A zero false-discovery fraction in this suite is not a precise rare-event limit.

## Reproducibility details

The machine-readable record is [`model-ablation-v1`](assets/ablation.json). It includes the generated sample origin, training-pool hash, seed, epochs, suite size and truth grid, fit settings, and per-model results. Reproduce the comparison from source and review the [encoder path](encoder.md) before drawing a conclusion.

<script src="../assets/ablation.js" defer></script>
