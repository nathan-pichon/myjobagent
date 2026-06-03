"""Local SQLite persistence — everything stays on the user's machine.

Replaces the original memory.json. Tracks jobs (with explainable breakdown),
runs, the application pipeline status, and the user's "not relevant" flag (the only
local source of truth on matching quality, and fuel for the Supervisor).
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_DB = "jobhunt.db"

PIPELINE_STATUSES = ("found", "interested", "applied", "interview", "offer", "rejected")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    url           TEXT PRIMARY KEY,
    dedup_key     TEXT,
    title         TEXT,
    company       TEXT,
    location      TEXT,
    contract      TEXT,
    score         INTEGER,
    breakdown     TEXT,        -- JSON: per-criterion sub-scores + gaps
    summary       TEXT,        -- French, user-facing
    source        TEXT,
    sources       TEXT,        -- JSON list of urls merged via dedup
    status        TEXT DEFAULT 'found',
    feedback      INTEGER DEFAULT 0,   -- -1=not relevant, 0=none (legacy 1=relevant)
    first_seen    REAL,
    last_seen     REAL
);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score);
CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  REAL,
    ended_at    REAL,
    steps       INTEGER,
    urls_seen   INTEGER,
    matches     INTEGER,
    stats       TEXT
);

CREATE TABLE IF NOT EXISTS visited (
    url        TEXT PRIMARY KEY,
    visited_at REAL
);

CREATE TABLE IF NOT EXISTS searches (
    query      TEXT PRIMARY KEY,
    ran_at     REAL
);

-- "Why-not": offers the engine looked at but discarded, with the reason.
-- Reassures the user ("nothing important was missed") and helps them tune criteria.
CREATE TABLE IF NOT EXISTS rejected (
    url        TEXT PRIMARY KEY,
    reason     TEXT,        -- e.g. "below_threshold", "not_a_job", "expired", "location", "stack"
    detail     TEXT,        -- human-readable, e.g. "score 38 < 50" or "Go primary, off-stack"
    score      INTEGER,
    seen_at    REAL
);
CREATE INDEX IF NOT EXISTS idx_rejected_reason ON rejected(reason);
"""


@dataclass
class Job:
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    contract: str = ""
    score: int = 0
    breakdown: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    source: str = ""

    @property
    def dedup_key(self) -> str:
        import re

        norm = lambda s: re.sub(r"\s+", " ", (s or "").lower().strip())  # noqa: E731
        return f"{norm(self.title)}|{norm(self.company)}|{norm(self.location)}"


# User feedback kinds — a single chosen reason per match, fuels the Supervisor.
FEEDBACK_KINDS = ("irrelevant", "outdated")


class Store:
    def __init__(self, path: str | Path = DEFAULT_DB):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self._migrate()
        self.conn.commit()

    def _migrate(self) -> None:
        """Idempotent schema migrations for existing local databases."""
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(jobs)")}
        if "feedback_kind" not in cols:
            self.conn.execute("ALTER TABLE jobs ADD COLUMN feedback_kind TEXT DEFAULT ''")
            # backfill: legacy feedback = -1 → 'irrelevant'
            self.conn.execute(
                "UPDATE jobs SET feedback_kind='irrelevant' WHERE feedback = -1 AND (feedback_kind IS NULL OR feedback_kind='')"
            )

    # --- jobs ------------------------------------------------------------- #
    def upsert_job(self, job: Job) -> bool:
        """Insert or merge a job (dedup by title+company+location).

        Returns True if this was a brand-new job (for digests/notifications).
        """
        now = time.time()
        cur = self.conn.execute(
            "SELECT url, sources FROM jobs WHERE dedup_key = ? OR url = ?",
            (job.dedup_key, job.url),
        )
        existing = cur.fetchone()
        if existing:
            sources = set(json.loads(existing["sources"] or "[]"))
            sources.add(job.url)
            self.conn.execute(
                "UPDATE jobs SET last_seen=?, score=?, breakdown=?, summary=?, sources=? WHERE url=?",
                (now, job.score, json.dumps(job.breakdown, ensure_ascii=False),
                 job.summary, json.dumps(sorted(sources)), existing["url"]),
            )
            self.conn.commit()
            return False
        self.conn.execute(
            """INSERT INTO jobs
               (url, dedup_key, title, company, location, contract, score,
                breakdown, summary, source, sources, first_seen, last_seen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (job.url, job.dedup_key, job.title, job.company, job.location,
             job.contract, job.score, json.dumps(job.breakdown, ensure_ascii=False),
             job.summary, job.source, json.dumps([job.url]), now, now),
        )
        self.conn.commit()
        return True

    def get_jobs(self, min_score: int = 0, status: str | None = None) -> list[dict]:
        q = "SELECT * FROM jobs WHERE score >= ?"
        params: list[Any] = [min_score]
        if status:
            q += " AND status = ?"
            params.append(status)
        q += " ORDER BY score DESC"
        rows = self.conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["breakdown"] = json.loads(d.get("breakdown") or "{}")
            d["sources"] = json.loads(d.get("sources") or "[]")
            out.append(d)
        return out

    def set_status(self, url: str, status: str) -> None:
        if status not in PIPELINE_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        self.conn.execute("UPDATE jobs SET status=? WHERE url=?", (status, url))
        self.conn.commit()

    def set_feedback_kind(self, url: str, kind: str | None) -> None:
        """Set the user's feedback on a match: 'irrelevant', 'outdated', or
        None/'' to clear. Keeps the legacy integer `feedback` in sync (-1 for
        any negative flag) so older queries still work."""
        kind = kind or ""
        if kind and kind not in FEEDBACK_KINDS:
            raise ValueError(f"Unknown feedback kind: {kind}")
        self.conn.execute(
            "UPDATE jobs SET feedback_kind=?, feedback=? WHERE url=?",
            (kind, -1 if kind else 0, url),
        )
        self.conn.commit()

    def quality_stats(self) -> dict[str, int]:
        row = self.conn.execute(
            "SELECT SUM(feedback_kind='irrelevant') irrelevant, "
            "SUM(feedback_kind='outdated') outdated, COUNT(*) total FROM jobs"
        ).fetchone()
        return {
            "irrelevant": row["irrelevant"] or 0,
            "outdated": row["outdated"] or 0,
            "flagged": (row["irrelevant"] or 0) + (row["outdated"] or 0),
            "total": row["total"] or 0,
        }

    # --- "Why-not": rejected offers --------------------------------------- #
    def record_rejection(self, url: str, reason: str, detail: str = "", score: int = 0) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO rejected (url, reason, detail, score, seen_at) VALUES (?,?,?,?,?)",
            (url, reason, detail, score, time.time()),
        )
        self.conn.commit()

    def get_rejections(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM rejected ORDER BY score DESC, seen_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def rejection_summary(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT reason, COUNT(*) c FROM rejected GROUP BY reason ORDER BY c DESC"
        ).fetchall()
        return {r["reason"]: r["c"] for r in rows}

    # --- crawl bookkeeping ------------------------------------------------ #
    def is_visited(self, url: str) -> bool:
        return self.conn.execute("SELECT 1 FROM visited WHERE url=?", (url,)).fetchone() is not None

    def mark_visited(self, url: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO visited VALUES (?,?)", (url, time.time()))
        self.conn.commit()

    def visited_count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) c FROM visited").fetchone()["c"]

    def recent_searches(self, limit: int = 15) -> list[str]:
        rows = self.conn.execute(
            "SELECT query FROM searches ORDER BY ran_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [r["query"] for r in rows]

    def mark_search(self, query: str) -> None:
        self.conn.execute("INSERT OR REPLACE INTO searches VALUES (?,?)", (query, time.time()))
        self.conn.commit()

    def record_run(self, started: float, steps: int, urls_seen: int, matches: int, stats: dict) -> None:
        self.conn.execute(
            "INSERT INTO runs (started_at, ended_at, steps, urls_seen, matches, stats) VALUES (?,?,?,?,?,?)",
            (started, time.time(), steps, urls_seen, matches, json.dumps(stats, ensure_ascii=False)),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
