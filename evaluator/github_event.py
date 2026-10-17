"""Read and validate a GitHub issue-comment event without shell interpolation."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, time, timezone

from .submission import parse_submission, SubmissionError
from .state import EvaluationStore


def main():
    event = {}
    try:
        event_path = Path(os.environ["GITHUB_EVENT_PATH"])
        event = json.loads(event_path.read_text(encoding="utf-8"))
        expected_issue = int(os.environ["SUBMISSIONS_ISSUE"])
        issue = event.get("issue", {})
        repository = event.get("repository", {}).get("full_name", "")
        if (issue.get("pull_request") or int(issue.get("number", -1)) != expected_issue
                or repository.casefold() != os.environ.get("GITHUB_REPOSITORY", "").casefold()):
            raise SubmissionError("Comment is not on the configured submissions issue")
        deadline_text = os.environ.get("SUBMISSION_DEADLINE", "").strip()
        if deadline_text:
            deadline = datetime.fromisoformat(deadline_text.replace("Z", "+00:00"))
            if deadline.tzinfo is None:
                if "T" not in deadline_text and " " not in deadline_text:
                    deadline = datetime.combine(deadline.date(), time.max, tzinfo=timezone.utc)
                else:
                    deadline = deadline.replace(tzinfo=timezone.utc)
            created_at = event.get("comment", {}).get("created_at")
            if not isinstance(created_at, str):
                raise SubmissionError("Comment timestamp is missing")
            submitted_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if submitted_at.tzinfo is None:
                raise SubmissionError("Comment timestamp must include a timezone")
            if submitted_at.astimezone(timezone.utc) > deadline.astimezone(timezone.utc):
                raise SubmissionError("Submission deadline has passed")
        submission = parse_submission(event.get("comment", {}).get("body", ""))
        values = {
            "valid": "true",
            "invalid_reason": "",
            "team": submission.team,
            "repository": submission.repository,
            "sha": submission.sha,
        }
    except (KeyError, OSError, TypeError, ValueError, SubmissionError):
        login = event.get("comment", {}).get("user", {}).get("login", "unknown-user")
        if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
            login = "unknown-user"
        values = {"valid": "false", "invalid_reason": "malformed",
                  "team": f"invalid-comment/{login}", "repository": "", "sha": ""}
        invalid = True
    else:
        invalid = False
        author = event.get("comment", {}).get("user", {}).get("login", "")
        if not isinstance(author, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", author):
            author = "unknown-user"
        owner = submission.repository.split("/", 1)[0]
        # A public repo's owner must initiate its team claim. Persisting this binding then
        # prevents a later commenter from replacing that team's current commit/leaderboard.
        state_dir = Path(os.environ.get("EVALUATOR_STATE_DIR", ".evaluator-state"))
        store = EvaluationStore(state_dir / "evaluation.sqlite", state_dir / "leaderboard.json")
        if not isinstance(author, str) or author.casefold() != owner.casefold() or not store.claim_team(
                submission.team, submission.repository, author):
            values["valid"] = "false"
            values["invalid_reason"] = "ownership"
            values["team"] = f"invalid-comment/{author}"
            invalid = True
    try:
        output = Path(os.environ["GITHUB_OUTPUT"])
        with output.open("a", encoding="utf-8", newline="\n") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")
    except (KeyError, OSError):
        print("Could not save the parsed submission status.", file=sys.stderr)
        return 2
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
