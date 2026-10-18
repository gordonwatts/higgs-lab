"""Command-line interface for evaluator utilities."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .local import score_local, score_local_submission
from .hosted import score_submission, score_final
from .security import SandboxError, snapshot_commit
from .submission import SubmissionError, parse_submission
from .state import EvaluationStore
from .submission import Submission


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m evaluator")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("parse", help="validate a submission line")
    p.add_argument("text", help="submission line")
    p = sub.add_parser("snapshot", help="fetch an exact public commit safely")
    p.add_argument("repository", help="GitHub OWNER/REPO")
    p.add_argument("sha", help="full 40-character commit SHA")
    p.add_argument("destination", type=Path)
    p = sub.add_parser("score-local", help="score the baseline or a local submission on a public suite")
    p.add_argument("--submission", type=Path, help="run this submission/ directory in the isolated sandbox")
    p = sub.add_parser("score-hosted", aliases=["score-commit"],
                       help="score a pinned commit on a trusted Docker-isolated evaluator")
    p.add_argument("--team", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--work-dir", type=Path, required=True)
    p.add_argument("--fresh", action="store_true", help="bypass cached result while keeping the sealed suite")
    p = sub.add_parser("record-invalid", help="record malformed issue submission status")
    p.add_argument("--team", required=True)
    p.add_argument("--state-dir", type=Path, required=True)
    p = sub.add_parser("score-final", help="freshly re-score each latest team commit")
    p.add_argument("--state-dir", type=Path, required=True)
    p.add_argument("--work-dir", type=Path, required=True)
    p = sub.add_parser("isolation-check", help="build and rehearse the hostile-code Docker sandbox")
    p.add_argument("--report", type=Path, default=Path("output/isolation-report.json"))
    args = parser.parse_args(argv)
    try:
        if args.command == "parse":
            result = parse_submission(args.text)
            print(json.dumps({"team": result.team, "repository": result.repository, "sha": result.sha}))
        elif args.command == "snapshot":
            print(snapshot_commit(args.repository, args.sha, args.destination))
        elif args.command == "score-local":
            result = score_local_submission(args.submission) if args.submission else score_local()
            print(json.dumps(result, indent=2, allow_nan=False))
            if args.submission and result.get("n", 0) == 0:
                return 2
        elif args.command in {"score-hosted", "score-commit"}:
            secret = os.environ.get("SEALED_SEED", "")
            store = EvaluationStore(args.state_dir / "evaluation.sqlite", args.state_dir / "leaderboard.json")
            result = score_submission(Submission(args.team, args.repository, args.sha), secret,
                                      store, args.work_dir, fresh=args.fresh)
            print(json.dumps(result, indent=2, allow_nan=False))
            if result.get("status") == "failed":
                return 2
        elif args.command == "record-invalid":
            store = EvaluationStore(args.state_dir / "evaluation.sqlite", args.state_dir / "leaderboard.json")
            secret = os.environ.get("SEALED_SEED", "")
            if secret:
                from .hosted import make_suite_id
                current_suite = make_suite_id(secret)
                store.set_active_suite(current_suite)
            else:
                current_suite = store.active_suite() or "submission-v1"
            store.record(args.team, "", "", current_suite, "invalid",
                         error="Malformed submission line; see the submission guide.")
        elif args.command == "score-final":
            secret = os.environ.get("SEALED_SEED", "")
            store = EvaluationStore(args.state_dir / "evaluation.sqlite", args.state_dir / "leaderboard.json")
            result = score_final(secret, store, args.work_dir)
            print(json.dumps({"teams": len(result), "fresh_final_pass": True}, indent=2))
            if any(item.get("status") == "failed" or item.get("summary", {}).get("n", 1) == 0
                   for item in result):
                return 2
        elif args.command == "isolation-check":
            from .isolation import perform_isolation_check
            report = perform_isolation_check(args.report)
            print(json.dumps(report, indent=2, sort_keys=True))
            if not report["passed"]:
                return 2
    except (SubmissionError, SandboxError, ValueError, RuntimeError) as exc:
        print(f"evaluator: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
