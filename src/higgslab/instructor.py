"""Idempotent GitHub workshop bootstrap and operations commands."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tomllib


ISSUE_TITLE = "HiggsLab workshop submissions"


class InstructorError(RuntimeError):
    pass


def _gh(args: list[str], *, input_text: str | None = None):
    try:
        return subprocess.run(["gh", *args], input=input_text, text=True, capture_output=True,
                              check=True, timeout=45).stdout.strip()
    except FileNotFoundError as exc:
        raise InstructorError("GitHub CLI (gh) is required for hosted workshop setup") from exc
    except subprocess.CalledProcessError as exc:
        # GitHub CLI diagnostics may contain request details; do not print their bodies.
        raise InstructorError(f"GitHub command failed: gh {' '.join(args[:3])}") from exc


def _config(path="workshop.toml"):
    with Path(path).open("rb") as f:
        config = tomllib.load(f).get("workshop", {})
    for key in ("name", "event_title", "submissions_open"):
        if key not in config:
            raise InstructorError(f"{path} is missing workshop.{key}")
    if type(config["submissions_open"]) is not bool:
        raise InstructorError("workshop.submissions_open must be true or false")
    return config


def _repo_info(repo):
    info = json.loads(_gh(["api", f"repos/{repo}"]))
    if info.get("full_name", "").casefold() != repo.casefold():
        raise InstructorError("GitHub returned a repository different from the requested target")
    if not info.get("default_branch"):
        raise InstructorError("Target repository has no default branch")
    if not info.get("permissions", {}).get("admin", False):
        raise InstructorError("Authenticated account needs repository admin access")
    return info


def _check_template_origin(info, config):
    expected = config.get("template_repository")
    source = info.get("template_repository")
    if config.get("source_mode") == "mirror":
        if config.get("mirror_import_allowed") is not True:
            raise InstructorError("Mirror setup requires explicitly setting mirror_import_allowed = true in workshop.toml")
        if info.get("fork"):
            raise InstructorError("Mirror import target must be a newly created repository, not a fork")
        expected = config.get("mirror_source_repository") or expected
        if not expected:
            raise InstructorError("Mirror setup must name mirror_source_repository in workshop.toml")
        encoded = json.loads(_gh(["api", f"repos/{info['full_name']}/contents/.higgslab-template.json"]))
        try:
            if encoded.get("encoding") not in (None, "base64"):
                raise ValueError("unsupported marker encoding")
            payload = "".join(encoded["content"].split())
            marker = json.loads(base64.b64decode(payload, validate=True))
        except (KeyError, ValueError, TypeError) as exc:
            raise InstructorError("Mirror import is missing a valid HiggsLab source marker") from exc
        if (not isinstance(marker, dict) or marker.get("schema_version") != 1
                or marker.get("template_marker") != "higgslab-workshop-template-v1"
                or str(marker.get("source_repository", "")).casefold() != str(expected).casefold()):
            raise InstructorError("Mirror source marker does not match the approved template repository")
        return
    if not expected or not isinstance(source, dict):
        raise InstructorError("Target must be a fresh repository created from the configured template")
    if source.get("full_name", "").casefold() != str(expected).casefold():
        raise InstructorError("Target repository was created from a different template")


def _check_isolation_report(report_path: str | None):
    if not report_path:
        raise InstructorError("Opening submissions requires a passing `higgslab instructor isolation-check` report")
    from evaluator.isolation import isolation_fingerprint
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise InstructorError("Could not read the local isolation rehearsal report") from exc
    if report.get("passed") is not True or report.get("fingerprint") != isolation_fingerprint():
        raise InstructorError("Isolation report failed or no longer matches the sandbox code; rerun isolation-check")


def _issue(repo):
    found = json.loads(_gh(["issue", "list", "--repo", repo, "--state", "all", "--limit", "100",
                            "--json", "number,title", "--search", f'in:title "{ISSUE_TITLE}"']))
    exact = [entry for entry in found if entry.get("title") == ISSUE_TITLE]
    if len(exact) > 1:
        raise InstructorError("More than one submissions issue exists; resolve duplicates before continuing")
    if exact:
        return int(exact[0]["number"])
    created = _gh(["issue", "create", "--repo", repo, "--title", ISSUE_TITLE,
                   "--body", "Post one line per submission: `team: https://github.com/OWNER/REPO @ FULL_SHA`." ])
    match = re.search(r"/issues/(\d+)\s*$", created)
    if not match:
        raise InstructorError("GitHub created the issue but returned an unrecognized URL")
    return int(match.group(1))


def init(repo: str, config_path="workshop.toml", isolation_report: str | None = None):
    config = _config(config_path)
    if config["submissions_open"]:
        _check_isolation_report(isolation_report)
    _gh(["auth", "status"])
    info = _repo_info(repo)
    _check_template_origin(info, config)
    issue_no = _issue(repo)
    secret_names = _gh(["secret", "list", "--repo", repo, "--json", "name"])
    names = {item["name"] for item in json.loads(secret_names)}
    if "SEALED_SEED" not in names:
        seed = secrets.token_hex(32)
        _gh(["secret", "set", "SEALED_SEED", "--repo", repo], input_text=seed)
        del seed
        secret_state = "created"
    else:
        secret_state = "already present; preserved"
    values = {
        "SUBMISSIONS_ISSUE": str(issue_no),
        "WORKSHOP_NAME": config["name"],
        "EVENT_TITLE": config["event_title"],
        "WORKSHOP_CONFIGURED": "true",
        "WORKSHOP_ENABLED": str(bool(config["submissions_open"])).lower(),
        "SUBMISSIONS_OPEN": str(bool(config["submissions_open"])).lower(),
    }
    for key in ("start_date", "end_date", "deadline", "contact"):
        if config.get(key):
            values[key.upper()] = str(config[key])
    existing_variables = json.loads(_gh(["variable", "list", "--repo", repo, "--json", "name,value"]))
    existing_names = {item["name"] for item in existing_variables}
    for key in ("START_DATE", "END_DATE", "DEADLINE", "CONTACT"):
        if key not in values and key in existing_names:
            _gh(["variable", "delete", key, "--repo", repo])
    for name, value in values.items():
        _gh(["variable", "set", name, "--repo", repo, "--body", value])
    return {"repo": repo, "issue": issue_no, "secret": secret_state,
            "hosted_scoring": "enabled" if config["submissions_open"] else "disabled",
            "pages": "configure Pages source as GitHub Actions and create github-pages environment"}


def doctor(repo: str, config_path="workshop.toml", isolation_report: str | None = None):
    config = _config(config_path)
    isolation_ok = True
    if config["submissions_open"]:
        try:
            _check_isolation_report(isolation_report)
        except InstructorError:
            isolation_ok = False
    info = _repo_info(repo)
    _check_template_origin(info, config)
    variables = json.loads(_gh(["variable", "list", "--repo", repo, "--json", "name,value"]))
    variables = {v["name"]: v["value"] for v in variables}
    secrets_json = json.loads(_gh(["secret", "list", "--repo", repo, "--json", "name"]))
    secrets = {s["name"] for s in secrets_json}
    issues = json.loads(_gh(["issue", "list", "--repo", repo, "--state", "all", "--limit", "100",
                             "--json", "number,title,state"]))
    matches = [i for i in issues if i["title"] == ISSUE_TITLE]
    checks = {
        "admin": bool(info.get("permissions", {}).get("admin")),
        "default_branch_present": bool(info.get("default_branch")),
        "submissions_issue_unique": len(matches) == 1,
        "sealed_seed_present": "SEALED_SEED" in secrets,
        "issue_variable_matches": len(matches) == 1 and variables.get("SUBMISSIONS_ISSUE") == str(matches[0]["number"]),
        "workshop_name_matches_config": variables.get("WORKSHOP_NAME") == config["name"],
        "event_title_matches_config": variables.get("EVENT_TITLE") == config["event_title"],
        "configured_marker_present": variables.get("WORKSHOP_CONFIGURED", "false").lower() == "true",
        "submissions_open_matches_config": variables.get("SUBMISSIONS_OPEN", "false").lower() == str(bool(config["submissions_open"])).lower(),
        "hosted_state_matches_config": variables.get("WORKSHOP_ENABLED", "false").lower() == str(bool(config["submissions_open"])).lower(),
        "local_isolation_gate_passed": isolation_ok,
    }
    for key in ("start_date", "end_date", "deadline", "contact"):
        checks[f"{key}_matches_config"] = variables.get(key.upper()) == (str(config[key]) if config.get(key) else None)
    return {"repo": repo, "checks": checks, "ok": all(v is True for v in checks.values())}


def finalize(repo: str, *, config_path="workshop.toml"):
    config = _config(config_path)
    info = _repo_info(repo)
    _check_template_origin(info, config)
    _gh(["variable", "set", "SUBMISSIONS_OPEN", "--repo", repo, "--body", "false"])
    _gh(["variable", "set", "WORKSHOP_ENABLED", "--repo", repo, "--body", "false"])
    matches = json.loads(_gh(["issue", "list", "--repo", repo, "--state", "open", "--limit", "100",
                              "--json", "number,title"]))
    for issue in matches:
        if issue["title"] == ISSUE_TITLE:
            _gh(["issue", "close", str(issue["number"]), "--repo", repo,
                 "--comment", "Submissions are closed. The final scoring run is being prepared."])
    requested_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    _gh(["variable", "set", "FINAL_SCORE_REQUESTED_AT", "--repo", repo, "--body", requested_at])
    _gh(["workflow", "run", "score-submission.yml", "--repo", repo, "--ref", info["default_branch"],
         "--field", "operation=final-score"])
    return {"repo": repo, "submissions_open": False, "issue_closed": True,
            "final_scoring": "dispatched", "repository_archived": False}


def _require_successful_final_run(repo: str, default_branch: str):
    try:
        runs = json.loads(_gh(["api", f"repos/{repo}/actions/workflows/score-submission.yml/runs?per_page=100"]))
    except (InstructorError, ValueError) as exc:
        raise InstructorError("Could not verify the final scoring workflow") from exc
    variables = json.loads(_gh(["variable", "list", "--repo", repo, "--json", "name,value"]))
    requested = next((item["value"] for item in variables if item["name"] == "FINAL_SCORE_REQUESTED_AT"), None)
    if not requested:
        raise InstructorError("No final scoring run has been requested by finalize")
    requested_dt = dt.datetime.fromisoformat(requested.replace("Z", "+00:00"))
    dispatched = [run for run in runs.get("workflow_runs", [])
                  if run.get("event") == "workflow_dispatch" and run.get("head_branch") == default_branch
                  and isinstance(run.get("created_at"), str)
                  and dt.datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) >= requested_dt]
    if not dispatched or dispatched[0].get("status") != "completed" or dispatched[0].get("conclusion") != "success":
        raise InstructorError("Archive is allowed only after the latest final scoring run succeeds")


def archive(repo: str, config_path="workshop.toml"):
    info = _repo_info(repo)
    config = _config(config_path)
    _check_template_origin(info, config)
    variables = json.loads(_gh(["variable", "list", "--repo", repo, "--json", "name,value"]))
    values = {item["name"]: item["value"].lower() for item in variables}
    if values.get("SUBMISSIONS_OPEN") != "false" or values.get("WORKSHOP_ENABLED") != "false":
        raise InstructorError("Close submissions with finalize before archiving")
    _require_successful_final_run(repo, info["default_branch"])
    _gh(["api", "--method", "PATCH", f"repos/{repo}", "-F", "archived=true"])
    return {"repo": repo, "repository_archived": True}


def reset(repo: str, *, suite: str, config_path="workshop.toml"):
    if suite not in {"preserve", "replace"}:
        raise InstructorError("Choose suite='preserve' or suite='replace' explicitly")
    config = _config(config_path)
    info = _repo_info(repo)
    _check_template_origin(info, config)
    _gh(["variable", "set", "WORKSHOP_ENABLED", "--repo", repo, "--body", "false"])
    _gh(["variable", "set", "SUBMISSIONS_OPEN", "--repo", repo, "--body", "false"])
    if suite == "replace":
        seed = secrets.token_hex(32)
        _gh(["secret", "set", "SEALED_SEED", "--repo", repo], input_text=seed)
        del seed
    return {"repo": repo, "suite": suite, "hosted_scoring": "disabled"}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="higgslab instructor")
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("init"); p.add_argument("--repo", required=True); p.add_argument("--config", default="workshop.toml"); p.add_argument("--isolation-report")
    p = subs.add_parser("doctor"); p.add_argument("--repo", required=True); p.add_argument("--config", default="workshop.toml"); p.add_argument("--isolation-report")
    p = subs.add_parser("finalize"); p.add_argument("--repo", required=True); p.add_argument("--config", default="workshop.toml")
    p = subs.add_parser("archive"); p.add_argument("--repo", required=True); p.add_argument("--config", default="workshop.toml")
    p = subs.add_parser("reset"); p.add_argument("--repo", required=True); p.add_argument("--suite", choices=("preserve", "replace"), required=True); p.add_argument("--config", default="workshop.toml")
    p = subs.add_parser("isolation-check", help="run hostile local Docker sandbox rehearsal")
    p.add_argument("--report", type=Path, default=Path("output/isolation-report.json"))
    args = parser.parse_args(argv)
    try:
        if args.command == "init": result = init(args.repo, args.config, args.isolation_report)
        elif args.command == "doctor": result = doctor(args.repo, args.config, args.isolation_report)
        elif args.command == "finalize": result = finalize(args.repo, config_path=args.config)
        elif args.command == "archive": result = archive(args.repo, config_path=args.config)
        elif args.command == "isolation-check":
            from evaluator.isolation import perform_isolation_check
            result = perform_isolation_check(args.report)
        else: result = reset(args.repo, suite=args.suite, config_path=args.config)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok", result.get("passed", True)) else 1
    except (InstructorError, OSError, ValueError) as exc:
        print(f"higgslab instructor: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
