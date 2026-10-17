# HiggsLab: From Events to Evidence

## Purpose

Build a reusable, student-facing H→WW analysis tutorial in **one source repository**, [`gordonwatts/higgs-lab`](https://github.com/gordonwatts/higgs-lab). A student should start with a working measurement, change just one component, test the change locally, and submit a Git commit for evaluation. The tutorial should support three connected paths: a supervised classifier, a small self-supervised event encoder with a classification head, and a statistical fit. The outcome is a measurement of Higgs signal strength μ with an uncertainty, not merely a classifier AUC.

**Proposed public title:** **HiggsLab: From Events to Evidence**. Use “Build a Higgs-to-WW measurement with machine learning and a fit” as its subtitle. The title covers the analysis and fit as well as the foundation-model path; `MiniHEP` can remain the name of the small encoder model.

This document is the implementation plan. The repository currently contains only this plan and an introductory README. The source material exists in the course repository and in Andrzej Novak's separate benchmark repository; it has not yet been migrated here.

## Source material and what to retain

| Source | What it contributes | Action |
| --- | --- | --- |
| [Delhi ML/AI session](https://indico.cern.ch/event/1714663/timetable/#sc-15-2-mlai) and its [work plan](https://docs.google.com/document/d/1VFZyrQ0SKJltVIGf49d8QOXkFlR28G58TUaqKQ0Pch0/edit) | The actual flow: physics framing, classifier teams, encoder teams, OpenCode-assisted work, and a final shared measurement. | Turn this into a paced student journey with optional branches. |
| [Course repository, main branch](https://github.com/gordonwatts/courses-hsf-india-October2026) | `01-tutorial-exercise-NN-JAX.ipynb`, `extra_functions.py`, `dataWW_d1.root`, and the introductory supervised exercise. | Adapt the concepts and correct the rough edges; do not require students to clone this second repo. |
| [Course repository, `minihep-4vector-tutorial` branch](https://github.com/gordonwatts/courses-hsf-india-October2026/tree/minihep-4vector-tutorial/minihep_tutorial) | The MiniHEP masked four-vector PyTorch prototype, schema, notebook, tests, and staged agent prompts. This branch is **not** on course `main`. | Bring it into this repo as a teaching path after validating it against the unified data contract. Preserve attribution and source commit `76cfa28`. |
| [H→WW benchmark kit](https://github.com/andrzejnovak/hsf-india-hww) | Public/sealed datasets, `run.sh`/`RESULT.json` contract, suite generator, fit examples, self-check, issue-comment submissions, evaluator, and leaderboard. | Consolidate the needed code and examples here, preserving attribution and history where practical. Check licensing with Andrzej before copying code verbatim; if permission is unclear, reimplement from the published interface and cite it. |
| [Andrzej's talk](https://andrzejnovak.github.io/talks/2026-10-13-hsf-india/index.html?profile=hack) | Motivation and the full analysis chain. | Use as a linked instructor reference and distill its ideas into shorter, progressively revealed pages. |

The benchmark's [guide](https://github.com/andrzejnovak/hsf-india-hww/blob/main/GUIDE.md) explains a useful distinction: a higher classifier AUC need not yield a better μ measurement. Its current `template_fit` baseline fits `(mT, mll)`; `tutorial_nn` and `nn_fit` insert a classifier score into the fit. The course's MiniHEP currently stops at masked reconstruction and event embeddings; it still needs a supervised probe and a connection to the measurement. Treat all reported workshop scores as historical examples, not acceptance thresholds for the new tutorial.

## Teaching contract

1. **One command to get a result.** The starter has a small, deterministic, CPU-capable template fit and a `run.sh <dataset_dir> <output_dir>` that produces valid `RESULT.json`. An instructor can demonstrate the full loop before students change code.
2. **One component at a time.** Stable functions for `load → features/encoder → score → templates → fit → result` let a student improve the features, classifier, encoder, histogram/binning, or fit without rebuilding the other stages. Provide one working baseline and focused TODOs at each seam, plus complete reference solutions kept separate from the starter.
3. **Common evaluation.** Every path must eventually produce the same result schema. Classifier AUC and masked reconstruction loss are diagnostics; the shared comparison is μ recovery, uncertainty calibration, and failure rate on generated suites. `mH` can be an optional advanced result, matching the current benchmark's treatment of mass as unscored.
4. **Agent use is explicit and optional.** Include short, staged OpenCode/NRP prompts, expected outputs, checks, and questions students should ask of generated code. No exercise requires an API token; manual coding and other assistants work. Never store tokens in notebooks, Git history, logs, or submissions.
5. **Two audience tracks in the prose.** The main path assumes Python but no particle-physics background. Sidebars explain H→WW→ℓνℓν, signal/background, simulation and event weights, MET, four-vectors, μ, templates, likelihood, uncertainty, and why a blind suite is needed. Advanced notes can derive the likelihood and attention model without blocking a CS student.

## Repository design

Target layout (names may be refined during implementation):

```text
README.md                     # short entry point and launch links
plan.md
pyproject.toml                # installable package and pinned teaching dependencies
mkdocs.yml
docs/                         # source Markdown for GitHub Pages
  index.md, setup.md, physics.md, data.md, analysis.md
  classifier.md, encoder.md, fit.md, agents.md, submission.md, faq.md
  instructor.md                # new-workshop deployment and operations runbook
notebooks/                    # short exploration notebooks; no saved traceback/output
src/higgslab/                 # shared data, features, models, templates, fit, CLI
student/                      # runnable starter and editable component interfaces
solutions/                    # instructor references, clearly separated
evaluator/                    # dataset generation, validation, scoring, publishing
datasets/public/              # small public benchmark, with provenance and checksum
tests/                        # contract, data integrity, fit, security, smoke checks
.github/workflows/            # CI, sealed scoring, docs/leaderboard deployment
```

Keep the **upstream** project in this one repository. Students can fork it and submit a commit hash; their forks are submissions, not a second tutorial dependency. The public dataset, starter, evaluator source, docs, and site source all live here. The sealed seed/truth is held only in GitHub Actions secrets or a private data store, never in Git or the Pages artifact. The previous benchmark repo becomes a credited historical source, not a required runtime checkout.

The README must prominently credit **Gordon Watts and Andrzej Novak as the tutorial's co-creators**, with links to their contributions and the 2026 Delhi workshop. It should also acknowledge the original course and benchmark contributors where their material is used. Keep the co-creator credit in the README and rendered docs landing page, not only in commit history or a buried acknowledgments file.

### Instructor deployment strategy

**Default: create one new GitHub repository from the `gordonwatts/higgs-lab` template for each workshop.** Once the tutorial is ready, mark that canonical repository as a template. The new repository is the workshop's single live repo: it contains the starter, docs, evaluator, Actions workflows, public data, and site source. Students fork **that** repo and submit their fork's commit SHA back to its submissions issue. Keep the canonical tutorial template separate so a later cohort starts without old teams, results, or a reused sealed suite. A normal `git clone` of the template is enough for local teaching and local scoring; it does not create the GitHub issue, repository secret, Actions settings, or Pages deployment needed for a hosted leaderboard. GitHub's template mechanism copies files into a new repository with a fresh history; it does not copy the original repository's issues and other workshop state ([GitHub template docs](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)).

The implementation should supply an **idempotent instructor bootstrap command** such as `higgslab instructor init --repo OWNER/WORKSHOP --name "Workshop name" --deadline ...` (or `./scripts/setup-workshop`), backed by `gh` where available. It should verify the intended repo is a fresh copy of this template, check GitHub authentication/admin access, create or locate the single submissions issue, generate and set a new random `SEALED_SEED` secret **only if absent**, save the issue number and public event metadata as repository variables/config, and print the remaining GitHub settings that need an instructor action. It must never print the seed, put it in a URL, write it into Git, or rotate it on a routine re-run. Include `doctor` and `reset`/`archive` commands; make reset explicitly preserve or intentionally replace the suite rather than silently changing scores. Avoid hard-coded repository names, issue `#1`, URLs, team names, and deadlines in code or docs.

The published `docs/instructor.md` should give this exact sequence, with copyable commands and screenshots only where the UI is unavoidable:

1. **Create the workshop repo.** Mark the canonical repo as a GitHub template once; select **Use this template → Create a new repository**, choose the instructor/organization as owner, and create a public workshop repo. Use only the default branch. Name the repo and workshop in one small config file (`workshop.toml` or similar), including the event title, dates/deadline, contact, and whether submissions are open. Run `git clone` on the new repo for local rehearsal. If an organization blocks template creation, document a one-time mirror/import fallback with the same checks.
2. **Bootstrap GitHub.** Enable Actions for the new repo; set minimum workflow permissions per job, with write access only for the trusted issue/status and Pages publisher jobs. Run the bootstrap command to create the submissions issue, set the fresh sealed seed, record the issue number, and turn on the event only after the dry run. Configure Pages to use the GitHub Actions publishing workflow, with the `github-pages` environment and its deployment permissions ([GitHub Pages workflow guide](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically)). Verify that README, docs, submission helper, issue parser, and workflow all derive the **new** repo URL and issue number.
3. **Check compute and data.** Confirm the public dataset checksum, local baseline result, exact Python environment, and a clean `higgslab check` run. Verify that the GitHub runner has enough time/storage for the planned sealed suite and that submitted code executes inside the restricted sandbox with no repository write token, network, seed, truth, or other teams' files. If that isolation check fails, leave hosted submissions disabled and use the documented controlled evaluator. GitHub explicitly warns that an `issue_comment` workflow that fetches and runs a fork's code can expose secrets or a write token if executed in the privileged job ([GitHub Actions security guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target)); this separation is a deployment gate.
4. **Rehearse as a student.** From a disposable student fork, modify one starter component, run local checks, push a commit, and post the exact submission line. Confirm the parser resolves the SHA, the sealed job runs, failure/status feedback appears, and the Pages leaderboard loads the new row. Keep the page open and confirm Refresh/polling updates it without a reload. Repeat with a second team and a resubmission. Remove or mark rehearsal rows before opening submissions; do not change the sealed suite merely to clear a row.
5. **Publish and operate.** Share one workshop URL (the Pages landing page), with clear links to the workshop repo, setup, student fork instructions, submissions issue, leaderboard, and optional Binder launch. Set `submissions_open=true` only after the rehearsal gate. During the workshop, monitor failed jobs and queue time, use `doctor` to compare configured state with the repo, and document the manual fallback if Actions is down. At the deadline, close new submissions, run a fresh final scoring pass on the same sealed suite, publish a timestamped final table, and archive the issue/site. Keep past cohort repos read-only and make the next workshop from the canonical template with a new seed and clean history.

**Fresh-repo acceptance test:** An instructor unfamiliar with the code can make a workshop repo from the template, run the bootstrap/check commands, see a working Pages site, and score a disposable student fork without editing Python or workflow YAML. The docs state which steps are automatic and which GitHub settings require the repo owner. Student forks should not activate hosted scoring themselves; guard hosted workflows with a workshop-enabled repository variable that exists only in the instructor repo.

Use a single canonical public data format for the exercise, likely the benchmark's `data/events.npz`, `mc/pool.npz`, and `mc/pool_meta.json`. Document how these files were derived from the reduced ATLAS Open Data ROOT file, their licensing, process labels, weights, and checksums; retain a reproducible preparation script rather than an unexplained binary. Reconcile the course ROOT schema with the benchmark schema before porting MiniHEP: the course loader uses `(px, py, pz, E)` with `lep_E`/`jet_E` in MeV and a MET proxy, while the benchmark NPZ has `pt, eta, phi` and treats leptons as massless. Define the token conversion once and test units, zero padding, labels, weights, and event identity. Training and public evaluation splits must be disjoint; fit scalers on training only. Ensure no event or derived duplicate crosses partitions.

## Student paths

| Path | Starting point | Student can change | First useful check | Shared finish |
| --- | --- | --- | --- | --- |
| **Measurement/fit** | Working `(mT, mll)` Poisson template fit and background normalization parameter. | Fit variables, binning, nuisance treatment, uncertainty method, optional mass scan. | Public truth recovery and local generated-suite pulls. | Valid `RESULT.json`. |
| **Supervised ML** | Small CPU classifier with known feature list and saved model; a score-to-template adapter. | Features, architecture, training weights, validation, score bins. | Train/validation AUC **and** μ precision/calibration after the fit. | Same `RESULT.json`. |
| **Event encoder** | MiniHEP five-token masked reconstruction notebook and frozen-encoder probe. | Masking, encoder, representation, probe/fine-tuning, comparison with supervised path. | Masked loss, held-out probe AUC, then μ precision/calibration. | Same `RESULT.json`. |

The encoder path must explain that a four-epoch, ~17k-parameter model trained on this sample is a **foundation-model teaching prototype**, not a general pretrained collider model. Add a direct comparison: raw/engineered features versus frozen MiniHEP embeddings versus fine-tuned embeddings, at equal train/validation splits and fit settings. Students should be able to present a useful negative result if the encoder does not improve μ.

## Evaluation and submissions

Adopt and version the existing [dataset](https://github.com/andrzejnovak/hsf-india-hww/blob/main/DATASET.md) and [evaluation contract](https://github.com/andrzejnovak/hsf-india-hww/blob/main/EVAL_CONTRACT.md) after reviewing them. A submission is a pinned public fork commit containing executable `submission/run.sh`; it runs without a network and writes finite, schema-valid `RESULT.json` with μ, its positive uncertainty, significance, and discovery flag. Trained weights must travel with the submitted code in an allowed format. Publish the runtime dependency and size/resource limits. Supply `higgslab check` and `higgslab score-local` commands that run the same validator on a public dataset and newly generated, locally known-truth suites. The local tool should show bias, slope, pull width, precision, false discoveries, and failures, with plots and plain-language interpretations.

For the hosted path, use a designated GitHub issue comment in the form `team: repo-url @ full-commit-sha`, or a similarly simple form with a versioned parser. Verify that the SHA belongs to the declared repository and pin that exact SHA; never execute a moving branch head. Queue and score each latest team submission, allow resubmission, keep a visible error/status for malformed or failing entries, and use the same sealed suite for comparable runs. Reserve a final fresh run. Use a trusted orchestration job with minimal `issues` permission; run untrusted submitted code in an isolated container/runner with no network, secrets, write token, or access to sealed truth/other teams. Enforce time, memory, file, and dependency limits, and test the isolation before inviting students. Generate datasets and collect aggregate results outside that sandbox. Do not expose per-dataset truth or logs that leak it.

Publish a **GitHub Pages** site from `docs/` with an independently generated `leaderboard.json` and accessible table/plots. A small script polls the JSON periodically and provides a manual Refresh button, run timestamp, and status so the table can update while the page stays open. The trusted publisher updates only the data artifact and deploys Pages; it does not rewrite README on every submission. Include baseline rows, latest-per-team results, prior attempts, score definition, uncertainty calibration, and links to exact submitted commits. Test cache behavior and a simultaneous submission race. Keep the README as a stable overview linking to the site.

## Build sequence and completion gates

### 0. Preserve and resolve source contracts

- Record exact source commits for the course `main` and MiniHEP branch and the benchmark kit; catalogue reusable files and their authorship/licensing.
- Decide the canonical dataset and check the ROOT→NPZ conversion, units, process weights, size, and reproducibility. Write a short migration note explaining any deliberate change from the 2026 workshop contract.
- Freeze `dataset-v1`, `submission-v1`, and `score-v1` schemas before writing the three paths.

**Gate:** a fresh checkout can inspect the public data and reproduce its metadata/checksums without either old repo.

### 1. Make the complete starter work

- Package the shared loader, derived physics variables, baseline templates/fit, CLI, starter `submission/run.sh`, environment, and local self-check.
- Make a small public benchmark and deterministic generated-suite command. Add checks for no leakage, weight normalization, result schema, repeatability, and recovery at μ = 0, 1, and a non-nominal value.
- Give students a 10–15 minute “clone, run, inspect, change one line, rerun” quickstart. A notebook is for seeing the data and fit; the command-line pipeline is the submission source of truth.

**Gate:** from a clean CPU checkout, one documented setup command plus the starter command yields a valid result, and the self-check passes twice identically.

### 2. Add the supervised path

- Port the instructional JAX network only after fixing its technical issues, or choose a single maintained PyTorch training stack for both paths to reduce setup cost. Keep the old notebook as cited inspiration, not a second mandatory environment.
- Use train/validation/held-out partitions, training-only preprocessing, sensible weight handling, and exportable inference weights. Provide score histograms, ROC/AUC, overtraining plots, and an adapter to the common fit.
- Demonstrate an improved classifier that does **not** automatically improve μ, then a feature or fit change that helps, using local suite evidence.

**Gate:** a student can swap only the classifier module and obtain a valid measurement; the baseline remains reproducible on CPU.

### 3. Add the event-encoder path

- Bring MiniHEP from `minihep-4vector-tutorial` into the unified package; keep its five-token mask and explicit MET-proxy/units teaching notes.
- Add frozen and optionally fine-tuned classification heads, using exactly the supervised path's split and fit. Keep a short CPU default; expose a longer/GPU option only as an extension.
- Add an ablation table and explanation of pretraining objective versus downstream measurement; test masking, padding, no labels in pretraining, and train-only scaling.

**Gate:** masked pretraining → probe → score templates → μ result runs end to end, and the comparisons use identical data partitions.

### 4. Harden the hosted evaluator and site

- Port/reimplement the benchmark's checker, suite generator, scorer, baseline, submission parser, cache, and Actions orchestration in this repo. Split trusted publishing from untrusted execution and perform explicit hostile-submission tests.
- Implement the parameterized, idempotent instructor bootstrap/doctor/finalize commands and a template-repo smoke test. Require no source edits or hard-coded issue/repo IDs to deploy a new workshop.
- Build and deploy the MkDocs site and polling leaderboard; document issue submission, status/failure messages, deadlines, and a fallback manual scoring procedure.
- Test two teams, resubmission, duplicate names, malformed comments, failed runs, simultaneous events, cache reuse, and a fresh final run on disposable repositories or fixtures before enabling a public event.

**Gate:** an end-to-end test submission produces a row on Pages, refreshes in an already-open page, links to the exact SHA, and cannot read secrets or sealed answers.

### 5. Teach and maintain it

- Write the physics/CS bridge pages, concise exercises, and `docs/instructor.md` with the template-to-live-repo setup, a suggested 3–4 hour and multi-day schedule, checkpoints, common failures, and sample presentations.
- Write the README and docs landing page with clear co-creator credit for Gordon Watts and Andrzej Novak and attribution for reused workshop material.
- Add CI for package tests, notebook smoke execution with cleared outputs, docs links/build, starter determinism, baseline scores, and evaluator contract. Run a fresh-machine CPU rehearsal and a Binder/Jupyter rehearsal, including persistence instructions for `/data` if NRP BinderHub remains the host.
- Pin the teaching environment and document optional NRP/OpenCode setup without embedding credentials. Verify any launch link and image dependency before publishing; keep the local setup usable if BinderHub or NRP is unavailable.

**Gate:** a new instructor can create a fresh workshop repo, deploy the site/evaluator from the repo instructions, rehearse a student submission, and open the event without source edits; a student unfamiliar with HEP can complete the starter and one chosen extension from the published pages.

## Decisions to settle early in implementation

- **Code reuse rights:** confirm Andrzej's permission or a license for benchmark code before importing it wholesale; retain his authorship in either case.
- **Primary runtime:** favor one PyTorch/NumPy/SciPy CPU environment for the new tutorial, with JAX as a linked historical exercise, unless a concrete teaching need justifies two stacks.
- **Mass:** keep μ at a known 125 GeV as the main scored task; offer fitted `mH` as an advanced exercise. This matches the workshop benchmark and prevents an extra mass objective from obscuring the core measurement.
- **Hosting:** first deploy on GitHub Actions/Pages with a secret sealed seed and a carefully isolated runner. If that cannot enforce the no-secret/no-network boundary, move scoring to a separate controlled service while keeping all tutorial and evaluator source in this repo.


