# Implementation and verification

Verified locally on 2026-10-16 (America/Los_Angeles). Nothing has been pushed or deployed.

## Delivered

- Installable, locked CPU environment and a runnable `submission/run.sh` starter, with a native Python equivalent on Windows.
- Versioned data, result, and score contracts; deterministic public toy data with checksums; an independently implemented converter exercised against the pinned course ROOT file.
- Disjoint training/validation/template samples, canonical four-vectors and MET proxy, physics features, regularized templates, nuisance-profiled Poisson fitting, and strict JSON validation.
- Supervised, frozen MiniHEP, and fine-tuned MiniHEP paths, portable reference models and manifests, learning curves/ROC/score plots, and a reproducible ablation study.
- Public local-suite scoring, actual edited-submission checks, commit-line helper, focused student seams and separate reference solutions.
- Restricted-container evaluator, pinned public commit retrieval, team ownership, cutoff handling, suite/version-aware cache, concurrent transactional state, final scoring, and fail-closed instructor operations.
- MkDocs tutorial, optional agent prompts and NRP/OpenCode guidance, Binder environment, parameterized workshop links, and a polling leaderboard with accessible tables/plots.
- CI and guarded documentation/evaluator/Pages workflows.

## Verification performed

| Check | Evidence |
| --- | --- |
| Full Python tests | **47 passed, 1 skipped**. The skip is a Windows symlink privilege test; Linux CI runs it. |
| Leaderboard JavaScript tests | **4 passed**, covering Refresh, polling, no-cache fetches, paths, hostile text and safe commit URLs. |
| Starter | `higgslab check` passes, executes the actual starter twice, and verifies data checksums and result determinism. |
| Package isolation | Built a wheel, installed its core dependencies into a fresh environment, and ran its starter self-check successfully. This is a fresh environment rehearsal, not a claim of a new physical machine. |
| Public fit | mu = **1.0343 ± 0.1116**, with planted mu=1, using the final baseline. |
| Recovery tests | Generated cases at mu=0, 1, and 1.7 recover within four quoted standard deviations and repeat identically. |
| Model comparison | All paths complete a common 24-case suite; machine-readable results and plots are in `docs/assets/ablation.json`. |
| Larger local baseline suite | 50 cases, zero failures, bias 0.0186, slope 0.9065, pull width 1.1557, RMS residual 0.1367, zero discoveries in 13 null cases. These finite-sample diagnostics are not a rare-discovery bound. |
| Data provenance | Pinned source commits; original 600,000-row course ROOT table inspected, converted, validated and fitted locally. ROOT data are not redistributed. |
| Notebooks | Both notebooks execute successfully in the CPU environment and remain committed with empty outputs and unique cell IDs. |
| Documentation | Strict MkDocs build and local Markdown link checker pass. Figures inspected visually. |
| Deployment files | All workflow YAML parses; tests check hosted permissions and disabled-by-default fork guards. |
| Instructor fixtures | Idempotent initialization preserves the seed; explicit replacement, isolation gating and template/mirror checks tested without remote mutations. |
| Real browser | An already-open local leaderboard updates via Refresh and automatic polling for two fixture teams and a resubmission, with exact commit links. Screenshot: `output/leaderboard-rehearsal.png` (local, not committed). Fixture rows were removed from the built preview afterward. |

## External acceptance gates still pending

The local teaching tutorial is runnable. The full hosted-workshop acceptance gate has **not** been passed, and hosted submissions remain closed in `workshop.toml`.

1. **Actual container isolation:** Docker's client is installed, but the engine was unavailable even after attempting to start Docker Desktop. The real `instructor isolation-check` report says `passed: false`. Unit fixtures verify command boundaries; they do not prove live isolation. A running Linux Docker engine is needed to execute the hostile rehearsal and produce a passing report before opening submissions.
2. **Fresh GitHub workshop / Pages:** no repository, secret, issue, fork push, Pages deployment, or hosted scoring run was created. These require a live workshop repository and would publish material before the requested local-only review. Follow `docs/instructor.md` after reviewing and publishing the template. The GitHub CLI is not installed in this environment.
3. **BinderHub / NRP:** local notebooks and CPU dependency installation are verified; no remote Binder session, NRP login, model call, launch URL, or `/data` persistence was verified. The runbook requires a cohort-specific rehearsal before advertising them.
4. **Original data redistribution:** no upstream code license was identified. The shipped dataset is explicitly synthetic. A real ATLAS workshop must establish the original release/license and derivation before distributing converted data. The converter and inspected source checksum are recorded in `PROVENANCE.md` and `DECISIONS.md`.

These distinctions are deliberate: mocked deployment checks are not reported as successful live deployments, and synthetic events are not described as ATLAS data.

## Start locally

```bash
uv sync --frozen --extra ml --extra dev
uv run higgslab check
uv run higgslab run datasets/public output/baseline
uv run mkdocs serve
```

The student journey begins in `docs/setup.md`; the operational runbook is `docs/instructor.md`. Design choices and corrections are recorded in `DECISIONS.md`.
