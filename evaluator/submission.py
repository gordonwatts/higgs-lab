"""Versioned, deliberately small parser for workshop issue submissions."""

from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlparse


_LINE = re.compile(
    r"^\s*team:\s*(?:(?P<team>[A-Za-z0-9][A-Za-z0-9_.-]{0,63})\s+)?"
    r"(?P<url>https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s+"
    r"@\s*(?P<sha>[0-9a-fA-F]{40})\s*$",
    re.IGNORECASE,
)


class SubmissionError(ValueError):
    """A user-facing submission syntax or validation error."""


@dataclass(frozen=True)
class Submission:
    team: str
    repository: str
    sha: str


def parse_submission(text: str) -> Submission:
    """Parse one exact ``team: NAME https://github.com/O/R @ SHA`` line."""
    matches = [m for line in text.splitlines() if (m := _LINE.fullmatch(line))]
    if len(matches) != 1:
        raise SubmissionError(
            "Expected exactly one line: team: NAME https://github.com/OWNER/REPO @ FULL_SHA"
        )
    match = matches[0]
    parsed = urlparse(match.group("url"))
    parts = parsed.path.strip("/").split("/")
    if parsed.netloc.lower() != "github.com" or len(parts) != 2:
        raise SubmissionError("Repository must be a public GitHub OWNER/REPO URL")
    owner, repo = parts
    if owner.startswith(".") or repo.startswith(".") or repo.endswith(".git"):
        raise SubmissionError("Use a canonical https://github.com/OWNER/REPO URL")
    repository = f"{owner}/{repo}"
    # Most participants fork the starter under a repository with the same name;
    # the owner login is the stable default team identity in that case.
    team = match.group("team") or owner
    return Submission(team, repository, match.group("sha").lower())
