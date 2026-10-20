# HiggsLab: From Events to Evidence

**Build a Higgs-to-WW measurement with machine learning and a statistical fit.**

HiggsLab is a practical tutorial for Python learners who are curious about particle physics and for physics learners curious about modern machine learning. Begin with a working measurement, change one component, and use a shared validation suite to decide whether the change improved the measurement.

**Co-created by [Gordon Watts](https://github.com/gordonwatts) and [Andrzej Novak](https://github.com/andrzejnovak)** for the [2026 HSF-India Delhi workshop](https://indico.cern.ch/event/1714663/timetable/#sc-15-2-mlai). The project builds on the workshop's [course materials](https://github.com/gordonwatts/courses-hsf-india-October2026) and the [H→WW benchmark interface](https://github.com/andrzejnovak/hsf-india-hww); see [attribution](attribution.md) for specific contributors and licensing notes.

<div id="workshop-links" aria-live="polite">Workshop-specific repository and submission links appear here after instructor setup.</div>
<script src="assets/workshop-links.js" defer></script>

!!! warning "Teaching data"
    The current exercise data are a **synthetic teaching surrogate, not ATLAS data**. They are useful for learning a reproducible analysis chain but are not an experimental result. See [data and provenance](data.md).

## What you'll do

Start with a table of **synthetic collision events**: each row describes two charged particles, any jets, and momentum that appears to be missing. Some patterns resemble a Higgs decay; other processes can look similar. You will:

1. Turn each event into a score using a simple physical variable or a machine-learning model. The score says how signal-like the event looks; it is not a Higgs measurement.
2. Group events by that score and compare their counts with predicted signal and background counts. A statistical fit estimates **signal strength μ**, the amount of Higgs-like signal relative to a reference prediction, together with its uncertainty.
3. Change one part of the analysis and repeat it on the same generated test samples. Check whether the estimate is more precise while still recovering the known signal strength and reporting reliable uncertainties.

The [MiniHEP encoder path](encoder.md) explores a foundation-model idea within this chain: learn patterns from events without using their signal/background labels, then reuse that representation in a labeled classifier. This may help when labels are limited; the exercise measures whether it helps here. The [physics bridge](physics.md) explains the event vocabulary, and the [analysis map](analysis.md) shows how each software stage contributes to the final estimate.

## Choose a route

- **Start here:** [install and make the baseline measurement](setup.md).
- **New to particle physics?** Read the [physics bridge](physics.md) alongside the [analysis map](analysis.md).
- **Interested in ML?** Try the [supervised classifier](classifier.md) or the [MiniHEP event encoder](encoder.md).
- **Interested in inference?** Follow the [template fit](fit.md).
- **Ready to share your work?** Follow [submission instructions](submission.md).

All three routes finish with the same reported signal strength μ and uncertainty. Compare your change against the baseline using recovery, uncertainty, and calibration; a well-supported explanation of why a change did not help is also a useful result.

## Suggested pacing

The guided baseline, one focused extension, and short presentations fit a 3–4 hour session. For a multi-day course, add the encoder comparison, a fit variation, and the optional agent exercises. Students can complete every task by hand; an AI coding assistant is optional and no task requires a service token.
