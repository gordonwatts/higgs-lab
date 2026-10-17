# Instructor operations

This runbook turns the canonical HiggsLab repository into one workshop's live repository. Each cohort gets its own repository, issue, sealed seed, leaderboard, and history. The canonical template remains a clean starting point for later workshops. A fresh deployment must be rehearsed before student submissions are enabled.

The workshop configuration lives in `workshop.toml`; the repository URL, issue number, dates, and team names must come from the new repository's state/configuration. Do not copy a prior workshop's values into source code or workflow files.

## 1. Create the workshop repository

Mark the canonical HiggsLab repository as a template once. In GitHub, choose **Use this template → Create a new repository**, select the instructor or organization as owner, and create a public repository using the default branch. GitHub copies the files into a new repository with fresh history; it does not copy the source repository's issues or other workshop state. See [GitHub's template repository guide](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).

If organizational policy prevents template creation, make a one-time mirror/import with the same single-default-branch and fresh-workshop-state checks. Do not carry an old issue, leaderboard, or sealed seed into a new cohort.

For this fallback, explicitly opt into the approved source in `workshop.toml` before running `init`:

```toml
[workshop]
source_mode = "mirror"
mirror_import_allowed = true
mirror_source_repository = "gordonwatts/higgs-lab"
```

`init` verifies that the new non-fork repository contains a `.higgslab-template.json` marker naming that source. A mirror without the explicit setting or matching marker is rejected. Use this only for a documented template-import fallback; normal workshop creation should use GitHub's template flow.

Edit `workshop.toml` in the new repo with the event name/title, dates, deadline, contact, and initial `submissions_open = false`. Clone the repository locally and rehearse commands there:

```bash
git clone https://github.com/OWNER/WORKSHOP.git
cd WORKSHOP
uv sync --extra ml --extra dev
uv run higgslab run datasets/public output/baseline
uv run higgslab check
```

Replace `OWNER` and `WORKSHOP` with the values for this cohort. The template intentionally contains no workshop-specific URL or issue ID.

## 2. Bootstrap GitHub and Pages

Enable GitHub Actions for the new repository. Keep default workflow permissions read-only. Grant write permissions only to the trusted issue/status job and the Pages publisher, scoped to the resources each job uses. Set Pages' source to **GitHub Actions** and create/configure the `github-pages` environment as required by your organization. See [GitHub Pages deployment guidance](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically).

Authenticate with GitHub CLI (`gh`) as a repository administrator, then run:

```bash
gh auth status
uv run higgslab instructor init --repo OWNER/WORKSHOP
uv run higgslab instructor doctor --repo OWNER/WORKSHOP
```

`init` creates or locates the single submissions issue, creates a random `SEALED_SEED` secret only if it is absent, stores the issue number and event metadata as repository variables, and leaves `WORKSHOP_ENABLED` and `SUBMISSIONS_OPEN` false. It does not reveal the seed. A routine re-run preserves an existing seed. `doctor` checks admin access, the unique issue, seed presence, and configuration values. Resolve all failed checks before continuing.

The `WORKSHOP_CONFIGURED` variable is set only in the instructor repository. Student forks should not receive it; the docs and evaluator workflows use it to prevent forks from publishing a workshop site or starting hosted scoring.

After GitHub Pages is configured, open **Actions → Build documentation → Run workflow**, choose the default branch, and set `publish` to `true` for the first site deployment. The publisher job runs only when `WORKSHOP_CONFIGURED=true`, a variable created by `init`. It includes the local synthetic baseline row on first deployment and restores the latest published `leaderboard.json` for later documentation-only deployments. Regular pushes build and validate docs without replacing the live leaderboard; scoring publishes later leaderboard snapshots through the trusted publisher workflow.

Review the workflows, README, docs, submission instructions, parser, and Pages URL for correct derivation from the new repo. The student submission endpoint must point to the new submissions issue; the site URL must be the new repo's Pages address. Student forks must not have the instructor-only enablement variable.

## 3. Check compute, data, and isolation

Confirm the public sample checksums and metadata, run the baseline, and require a clean `higgslab check`. Confirm the exact Python environment and the planned suite's runner time, disk, and memory requirements. Test that submitted code runs in the restricted sandbox without network, secrets, write tokens, sealed seed/truth, or another team's files.

This is a deployment gate. GitHub warns that privileged `issue_comment` workflows that fetch and execute fork code can expose secrets or write tokens. Keep trusted orchestration separate from untrusted execution, and give the execution environment no privileged credentials. Review [GitHub's Actions security guidance](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target). If isolation cannot be demonstrated, leave hosted scoring disabled and use a controlled local/manual evaluator.

Run the hostile-submission rehearsal on a Linux machine with a running Docker engine:

```bash
uv run higgslab instructor isolation-check --report output/isolation-report.json
```

The report must say `passed: true` and match the current sandbox implementation. Failure leaves hosted scoring disabled. This tests secret and host-file isolation, read-only source, blocked network, symlink refusal, time and output limits, and successful result collection. It is separate from the ordinary student self-check and must be rerun after changing the sandbox.

## 4. Rehearse as a student

Use a disposable student fork. Make one starter change, run the local checks, push a commit, and post the exact submission line from [the student instructions](submission.md). Confirm that the parser resolves the full SHA in the declared repository, the pinned commit runs, status feedback appears, and a row reaches the Pages leaderboard. Leave the leaderboard page open and confirm both timed polling and the Refresh button update it.

Repeat with a second team and with a resubmission. Rehearse malformed comments and a failing result too, so the team can see clear status feedback. Remove or mark rehearsal rows before opening the event; keep the sealed suite fixed while doing so. Check the exact commit links and ensure no suite truth values appear in the published JSON or logs.

## 5. Publish and operate

Share one Pages landing-page URL. It should link to the workshop repository, setup guide, fork/submission instructions, submissions issue, and leaderboard. The repository includes an optional Binder environment, but only add a Binder launch link after validating the actual host URL, CPU package install, and any `/data` persistence behavior for this cohort. After every rehearsal gate passes, set `submissions_open = true` in `workshop.toml`, then run:

```bash
uv run higgslab instructor init --repo OWNER/WORKSHOP --isolation-report output/isolation-report.json
uv run higgslab instructor doctor --repo OWNER/WORKSHOP --isolation-report output/isolation-report.json
```

Opening submissions requires the passing report. Rehearse the hosted path with disposable commits before sharing the public invitation; close it again if any gate fails.

During the workshop, monitor failed jobs and queue time. Run `uv run higgslab instructor doctor --repo OWNER/WORKSHOP` to compare repository configuration with the local workshop file. If Actions is unavailable or isolation is uncertain, use the documented controlled evaluator and report the fallback to students.

At the deadline, stop new submissions, make a fresh final scoring pass for every team's latest pinned commit against the common 30-case suite (the final pass bypasses cached scores), publish a timestamped final table, and close/archive the submissions issue and Pages/site according to the event's retention policy. Use `finalize` to close submissions and disable hosted scoring:

```bash
uv run higgslab instructor finalize --repo OWNER/WORKSHOP
```

This closes new submissions and dispatches the fresh final pass with the existing seed. Wait for the latest **Score workshop submission** workflow to finish successfully and inspect its published table. Only then archive:

```bash
uv run higgslab instructor archive --repo OWNER/WORKSHOP
```

The archive command refuses to proceed while the latest requested final pass is queued, running, or failed. The repository archive preserves the existing Pages site according to GitHub's settings; decide separately whether the past cohort's site should remain public.

When resetting a workshop, name whether the sealed suite stays fixed or is replaced:

```bash
uv run higgslab instructor reset --repo OWNER/WORKSHOP --suite preserve
uv run higgslab instructor reset --repo OWNER/WORKSHOP --suite replace
```

`replace` creates a new sealed seed and invalidates direct score comparisons with the old suite. Use it only as an intentional event reset. Keep completed cohort repositories read-only, and start the next cohort from the canonical template with a new seed and clean history.

## Schedule options

| 3–4 hour workshop | Multi-day workshop |
| --- | --- |
| 20 min: physics and event record | Day 1: setup, physics, and baseline reproduction |
| 20 min: install and baseline | Day 2: supervised classifier and validation |
| 45 min: choose one fit or classifier change | Day 3: MiniHEP, frozen probe, and fine-tuning |
| 45 min: generated-suite comparison | Day 4: templates, fit variations, and uncertainty calibration |
| 45 min: optional MiniHEP/agent exploration | Day 5: submissions, peer review, and presentations |
| 30 min: presentations and discussion | Allow additional time for compute setup and instructor review. |

## Common teaching failures

- **AUC becomes the only objective:** ask for μ recovery and pull-width evidence too.
- **Students compare different splits or fit settings:** return to the common dataset partitions and record the changed component.
- **The encoder is described as a general pretrained model:** clarify that it is a small teaching prototype trained on this sample.
- **A synthetic sample is described as ATLAS data:** correct the provenance claim before presentation or publication.
- **Hosted scoring is enabled before an isolation rehearsal:** disable it and switch to the controlled fallback.

Ask teams to present the question, one changed component, their prediction, baseline and changed metrics, limitations, and what they would try next. A clearly explained negative result is a successful workshop outcome.
