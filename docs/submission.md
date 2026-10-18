# Submit your work

Submit a pinned commit from a public fork under your own GitHub user account so the workshop can reproduce exactly the code you ran. This deployment requires a user-owned repository: the account that owns the fork must post the first submission line, and that same account must post any resubmissions. The evaluator binds the team, repository, and author claims and rejects a different commenter. Hosted submissions are enabled only in the instructor's workshop repository; a student fork does not activate scoring by itself.

## 1. Make and check a commit

Fork the workshop repository, clone your fork, and complete the quickstart. Make one focused change, then run:

```bash
uv run higgslab check
uv run python submission/analysis.py datasets/public output/public
uv run higgslab score-local --submission submission --output output/local-suite --count 12 --seed 71
```

Include any model JSON needed by your submission. The evaluator runs `submission/run.sh <dataset_dir> <output_dir>` against a pinned commit. The script must work without network access and write a valid `RESULT.json` in its output directory. Do not include credentials, unrelated large files, or generated data that should not be shared.

## 2. Push, then copy the full commit SHA

Push your branch to your public fork. Generate the exact pinned line from your clean, committed checkout:

```bash
uv run higgslab submission-line
```

This derives the public fork URL from `origin` and includes your full 40-character commit SHA. It prints the line without posting it. You can also copy the SHA from your Git client or commit page. A branch name or shortened SHA can move or identify the wrong code, so it cannot serve as a reproducible submission.

## 3. Post the submission line

Open the dynamically generated submissions-issue link on the [workshop landing page](index.md#workshop-links), then post exactly one line in this form:

```text
team: https://github.com/OWNER/REPOSITORY @ FULL_40_CHARACTER_SHA
```

Your team name is inferred from the repository owner's GitHub login (`OWNER`), so student forks with the same repository name remain distinct. If your instructor has enabled named teams, use the extended form `team: TEAM_NAME https://github.com/OWNER/REPOSITORY @ FULL_40_CHARACTER_SHA`. Use one stable team name; a new comment with the same team name is a resubmission, and the latest attempt is shown in the leaderboard. The evaluator checks that the commit belongs to the declared repository. Never include a secret or access token in the comment.

## 4. Read the status

The comment receives a queued, running, complete, or failed status. A completed result links to the exact submitted commit. Read the [leaderboard](leaderboard.md) for the latest team row, previous attempts, the run timestamp, and the score definition. The sealed hosted suite has 30 cases; the public local suite is smaller and has visible truth for debugging. Use Refresh if the page is already open. Errors should be short and actionable; if your result fails validation, inspect it locally with `higgslab check`, commit the fix, and submit again.

If hosted evaluation is unavailable, ask the instructor for the documented local/manual fallback. The workshop may close submissions at its stated deadline and perform a final run on the common sealed suite.
