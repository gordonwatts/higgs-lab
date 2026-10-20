# HiggsLab: From Events to Evidence

**Build a Higgs-to-WW measurement with machine learning and a statistical fit.**

HiggsLab is a hands-on tutorial in which you start from event records, make a signal-versus-background model, build signal and background templates, and estimate the signal strength, μ. The same measurement can be reached with engineered features, a small event encoder, or changes to the statistical fit. A higher classifier AUC is useful evidence about classification; it does not guarantee a more precise or better calibrated measurement.

**HiggsLab's co-creators are [Gordon Watts](https://github.com/gordonwatts) and [Andrzej Novak](https://github.com/andrzejnovak).** The teaching flow grew from the [2026 HSF-India Delhi ML/AI workshop](https://indico.cern.ch/event/1714663/timetable/#sc-15-2-mlai). The supervised exercise adapts ideas from [Gordon's course repository](https://github.com/gordonwatts/courses-hsf-india-October2026); the benchmark and submission design acknowledge [Andrzej's H→WW benchmark kit](https://github.com/andrzejnovak/hsf-india-hww). MiniHEP also credits its course-branch authors in the [attribution page](docs/attribution.md). HiggsLab is an independent teaching implementation; no source code is copied from the benchmark kit without a verified reuse license.

> **Data provenance:** the current generated sample is a **synthetic teaching surrogate, not ATLAS data**. It is designed to teach the analysis workflow and does not reproduce an ATLAS measurement or claim detector simulation provenance. The [data guide](docs/data.md) documents optional ROOT conversion for the course source, with unit checks and a licensing gate before redistribution.

## Get started

Students: use a full fork of your instructor's workshop repository and start with the [student workspace guide](docs/student-workspace.md). Your executable editing surface is `submission/`.

```bash
uv sync --extra ml --extra dev
uv run higgslab run datasets/public output
uv run higgslab check
```

The [10–15 minute quickstart](docs/setup.md) explains the commands and how to inspect the result. You can continue with the [physics bridge](docs/physics.md), [analysis map](docs/analysis.md), [classifier path](docs/classifier.md), [MiniHEP encoder path](docs/encoder.md), and [statistical fit](docs/fit.md). The [notebook](notebooks/01-explore.ipynb) is an optional data tour; the command-line pipeline is the source of truth for a submission.

See [implementation and verification](IMPLEMENTATION_STATUS.md) for tested behavior and the remaining live-deployment gates, and [the decision log](DECISIONS.md) for design choices and corrections.

## Workshop site

The documentation site is the stable entry point for students and instructors. When a workshop copy is published, its Pages URL and submission issue are generated from that repository's configuration rather than being embedded in this template. Hosted scoring is opt-in and remains disabled until the instructor rehearses the complete workflow.

- [Open the tutorial](docs/index.md)
- [Submit a commit](docs/submission.md)
- [Instructor operations](docs/instructor.md)
- [FAQ and troubleshooting](docs/faq.md)

## Workshop format

The core path fits a **3–4 hour workshop**; supervised learning, MiniHEP, and extended fit studies can also run as a multi-day project. Students can work entirely by hand. Optional AI coding-agent prompts are provided as structured exercises; they require no API token and work with any assistant or editor.

## Attribution and license

HiggsLab is an independent implementation. The Delhi workshop plan, the course repository, the MiniHEP course branch, and Andrzej Novak's benchmark kit are credited where their ideas or interfaces inform the tutorial. See [attribution and sources](docs/attribution.md) for authorship and licensing notes. The repository license covers only files explicitly marked as HiggsLab material; it does not imply a license for upstream source material.
