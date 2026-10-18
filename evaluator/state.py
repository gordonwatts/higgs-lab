"""Transactional queue, attempt history, cache, and atomic leaderboard output."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import time


SCHEMA_VERSION = 1
SCORE_DEFINITION = (
    "score-v1: 100 * (baseline RMS mu residual / submitted RMS mu residual) * "
    "min(pull width, 1/pull width) * recovery fraction; score is zero when fewer than "
    "80% of cases are valid, mu recovery slope <= 0.2, null false-discovery fraction > 0.2, "
    "absolute pull mean > 1, pull width is undefined, or submitted residual RMS is zero."
)


class EvaluationStore:
    def __init__(self, db_path: str | Path, leaderboard_path: str | Path):
        self.db_path = Path(db_path)
        self.leaderboard_path = Path(leaderboard_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.leaderboard_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team_key TEXT NOT NULL,
                    team TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    sha TEXT NOT NULL,
                    suite_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
                CREATE INDEX IF NOT EXISTS attempts_cache ON attempts(repository, sha, suite_id, status);
                CREATE INDEX IF NOT EXISTS attempts_team ON attempts(team_key, id);
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS team_claims (
                    team_key TEXT PRIMARY KEY,
                    repository TEXT NOT NULL UNIQUE,
                    author TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
                );
            """)

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=30, isolation_level="IMMEDIATE")
        db.row_factory = sqlite3.Row
        return db

    def cached_result(self, repository: str, sha: str, suite_id: str):
        with self._connect() as db:
            row = db.execute(
                "SELECT result_json FROM attempts WHERE repository=? AND sha=? AND suite_id=? AND status='complete' ORDER BY id DESC LIMIT 1",
                (repository.lower(), sha.lower(), suite_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def latest_submissions(self):
        """Return latest parseable commit per team for the fresh final pass."""
        with self._connect() as db:
            active = db.execute("SELECT value FROM metadata WHERE key='active_suite'").fetchone()
            if active:
                rows = db.execute("SELECT * FROM attempts WHERE suite_id=? ORDER BY id",
                                  (active[0],)).fetchall()
            else:
                rows = db.execute("SELECT * FROM attempts ORDER BY id").fetchall()
        latest = {}
        for row in rows:
            if row["repository"] and row["sha"]:
                latest[row["team_key"]] = row
        return [dict(row) for row in sorted(latest.values(), key=lambda r: r["team_key"])]

    def active_suite(self) -> str | None:
        with self._connect() as db:
            row = db.execute("SELECT value FROM metadata WHERE key='active_suite'").fetchone()
        return row[0] if row else None

    def claim_team(self, team: str, repository: str, author: str) -> bool:
        """Bind a team/repository to its first submitting GitHub account."""
        team_key, repo, login = team.casefold(), repository.lower(), author.casefold()
        try:
            with self._connect() as db:
                existing = db.execute(
                    "SELECT team_key,repository,author FROM team_claims WHERE team_key=? OR repository=?",
                    (team_key, repo),
                ).fetchall()
                if existing:
                    return (len(existing) == 1 and existing[0]["team_key"] == team_key
                            and existing[0]["repository"] == repo and existing[0]["author"] == login)
                db.execute("INSERT INTO team_claims(team_key,repository,author) VALUES(?,?,?)",
                           (team_key, repo, login))
        except sqlite3.IntegrityError:
            # Concurrent first submissions race on unique team/repository constraints;
            # exactly one owner wins the binding.
            with self._connect() as db:
                row = db.execute("SELECT team_key,repository,author FROM team_claims WHERE team_key=?",
                                 (team_key,)).fetchone()
            return bool(row and row["repository"] == repo and row["author"] == login)
        return True

    def set_active_suite(self, suite_id: str) -> None:
        """Select the only cohort shown as current and eligible for final scoring."""
        with self._connect() as db:
            db.execute("INSERT INTO metadata(key,value) VALUES('active_suite',?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (suite_id,))
        self.publish()

    def set_baseline(self, summary: dict, suite_id: str | None = None) -> None:
        with self._connect() as db:
            encoded = json.dumps(summary, allow_nan=False, sort_keys=True)
            if suite_id is not None:
                db.execute("INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                           (f"baseline:{suite_id}", encoded))
            db.execute("INSERT INTO metadata(key,value) VALUES('baseline',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (encoded,))
            if suite_id is not None:
                db.execute("INSERT INTO metadata(key,value) VALUES('baseline_suite',?) "
                           "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (suite_id,))
        self.publish()

    def record(self, team: str, repository: str, sha: str, suite_id: str,
               status: str, result: dict | None = None, error: str | None = None) -> int:
        if status not in {"queued", "running", "complete", "failed", "invalid"}:
            raise ValueError("Unknown attempt status")
        # Status text is public. Bound length and strip control characters to prevent markup/log injection.
        safe_error = "".join(ch for ch in (error or "") if ch.isprintable())[:240]
        with self._connect() as db:
            cur = db.execute(
                "INSERT INTO attempts(team_key,team,repository,sha,suite_id,status,result_json,error) VALUES(?,?,?,?,?,?,?,?)",
                (team.casefold(), team, repository.lower(), sha.lower(), suite_id, status,
                 json.dumps(result, allow_nan=False, sort_keys=True) if result is not None else None,
                 safe_error or None),
            )
            row_id = cur.lastrowid
        self.publish()
        return row_id

    def publish(self, baseline: list[dict] | None = None, score_definition: str = SCORE_DEFINITION) -> None:
        """Serialize latest team state and history; replace the public JSON atomically."""
        db = self._connect()
        db.execute("BEGIN IMMEDIATE")
        try:
            rows = db.execute("SELECT * FROM attempts ORDER BY id").fetchall()
            active_suite_row = db.execute("SELECT value FROM metadata WHERE key='active_suite'").fetchone()
            active_suite = active_suite_row[0] if active_suite_row else None
            saved_baseline = (db.execute("SELECT value FROM metadata WHERE key=?", (f"baseline:{active_suite}",)).fetchone()
                              if active_suite is not None else None)
            baseline_matches_active = saved_baseline is not None
            if saved_baseline is None:
                saved_baseline = db.execute("SELECT value FROM metadata WHERE key='baseline'").fetchone()
            baseline_suite_row = db.execute("SELECT value FROM metadata WHERE key='baseline_suite'").fetchone()
            baseline_suite = baseline_suite_row[0] if baseline_suite_row else active_suite
            if baseline is None and saved_baseline and (active_suite is None or baseline_matches_active or baseline_suite == active_suite):
                baseline = [{"team": "HiggsLab baseline", "result": json.loads(saved_baseline[0])}]
            history = []
            latest = {}
            for row in rows:
                item = {
                    "team": row["team"], "repository": row["repository"], "sha": row["sha"],
                    "status": row["status"],
                    "result": json.loads(row["result_json"]) if row["result_json"] else None,
                    "error": row["error"], "timestamp": row["created_at"],
                    "suite_scope": "active" if active_suite is None or row["suite_id"] == active_suite else "prior suite",
                }
                history.append(item)
                if active_suite is None or row["suite_id"] == active_suite:
                    latest[row["team_key"]] = item
            document = {
                "schema_version": SCHEMA_VERSION,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "score_definition": score_definition,
                "cohort_scope": "active suite only; prior-suite history is retained for reference",
                "baseline": baseline or [],
                "latest": sorted(latest.values(), key=lambda x: x["team"].casefold()),
                "history": history,
            }
            fd, tmp_name = tempfile.mkstemp(prefix=".leaderboard-", suffix=".tmp", dir=self.leaderboard_path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump(document, stream, allow_nan=False, indent=2, sort_keys=True)
                    stream.write("\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp_name, self.leaderboard_path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
            db.commit()
        finally:
            db.close()
