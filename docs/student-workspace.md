# Your student workspace

Use a **full fork of the instructor's workshop repository** for this workshop. Start with the [Quickstart](setup.md), run commands from the repository root, and concentrate on `submission/`. You do not need to understand every folder to make an experiment.

| Your next action | Where to look |
| --- | --- |
| Run the baseline and inspect its result | [Quickstart](setup.md), `output/RESULT.json` |
| Change the analysis that will be evaluated | `submission/analysis.py` |
| Include a trained classifier | `submission/model.json`; see the [classifier](classifier.md) and [encoder](encoder.md) paths |
| Change the submission entry point on Linux | `submission/run.sh` |
| Find a useful experiment | [Analysis map](analysis.md); `student/components.py` contains sketches to copy into the executable submission |
| Explore public events | `datasets/public/` and optional `notebooks/01-explore.ipynb` |
| Check, score, commit, and submit | [Submission instructions](submission.md) |

`higgslab run` uses the shared reference pipeline. Run `python submission/analysis.py`, `higgslab check`, and `higgslab score-local --submission submission` to exercise your changes. Editing a sketch in `student/components.py` alone does not change the submitted analysis. Generated outputs under `output/` are local scratch files.

The remaining folders support your workspace: `src/higgslab/` is the shared library; `pyproject.toml` and `uv.lock` pin the environment; `contracts/` defines the data and result interfaces. Leave these at the instructor's workshop version for a comparable result. `evaluator/`, `.github/`, `scripts/`, and instructor documentation support workshop operations. `tests/` checks the implementation, and `solutions/` contains reference implementations to inspect when instructed. None is a required editing surface for the first exercise.

## What travels with your submission

Commit the executable analysis, `run.sh`, and any required model JSON **inside `submission/`**. The hosted evaluator fetches only that subtree at your full commit SHA. Changes to `src/higgslab/`, `student/`, datasets, dependencies, or files elsewhere in your fork do not travel with it. The trusted evaluator supplies the library, runtime, and dataset contracts for the workshop. If an experiment needs a helper, put it in `submission/` and import it there.

Keep the workshop checkout and lock file together rather than copying a few folders into a new repository. That preserves the synthetic sample, provenance, license, and package version used for local experiments. If your local library and the instructor's trusted library differ, resolve that version difference before comparing local and hosted scores.

## Why a full fork?

For this small repository, navigation gives students a focused workspace without introducing a second distribution to synchronize. A manually maintained starter would duplicate the library, data, contracts, and instructions. A generated kit could eventually omit operations, workflows, and solutions, but would need a manifest tying the canonical source SHA, dependency lock, public-data hashes, contract versions, and evaluator runtime together. It would also need its own fresh-copy and hosted rehearsal whenever those inputs change. We are retaining the full fork until that infrastructure has a demonstrated benefit.

The local regression rehearsal makes a fresh clone, changes the executable submission, trains a model, checks deterministic output, scores generated cases, commits the submission, and checks the submission exported at that exact SHA. This checks the local workflow and commit boundary. Actual issue posting, account ownership checks, and hosted status publication require the instructor's configured workshop and its [live rehearsal](instructor.md); they are not simulated by this local check.
