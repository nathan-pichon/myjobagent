"""Supervisor — between-runs prompt self-improvement.

Refactor of utils/supervisor.py onto the new package. Two signal sources:
 1. Agent failures logged during a run (malformed JSON, false positives).
 2. The user's 'not relevant' flags on matches (the local truth on quality).

It rewrites the ACTIVE prompt files under jobhunt/prompts/ surgically. Opt-in:
only runs when explicitly invoked (mja tune), never silently, so a small
model can't degrade prompts behind the user's back.
"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

from jobhunt.config import JobHuntConfig
from jobhunt.engine.prompts import PROMPTS_DIR
from jobhunt.llm.base import get_provider
from jobhunt.store import Store

console = Console()


def collect_feedback_signal(store: Store, limit: int = 20) -> list[str]:
    """Turn 'not relevant'-flagged matches into improvement notes for the Recruteur."""
    rows = store.conn.execute(
        "SELECT title, company, score, summary FROM jobs WHERE feedback = -1 ORDER BY score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [
        f"User marked as NOT relevant despite score {r['score']}: "
        f"{r['title']} @ {r['company']} — {r['summary'][:120]}"
        for r in rows
    ]


def tune_recruteur(cfg: JobHuntConfig, store: Store, *, dry_run: bool = True) -> str | None:
    """Propose (and optionally apply) a surgical Recruteur prompt revision based
    on the offers the user flagged 'not relevant'. Returns the proposed prompt,
    or None if no signal yet."""
    notes = collect_feedback_signal(store)
    if not notes:
        console.print("[dim]No 'not relevant' flags yet — nothing to tune.[/]")
        return None

    active = PROMPTS_DIR / "recruteur.md"
    current = active.read_text(encoding="utf-8")
    meta = (
        "You are the Supervisor. Improve the [RECRUITER] agent prompt below so it stops "
        "over-scoring offers the user rejected. Keep it in English, preserve the French-summary "
        "rule and the {{ profile }}/{{ job_text }} variables, keep the HARD GATES. Make surgical "
        "additions only (examples/counter-examples), do not rewrite wholesale.\n\n"
        "USER FEEDBACK (false positives to fix):\n" + "\n".join(f"- {n}" for n in notes) +
        "\n\nCURRENT PROMPT:\n```\n" + current + "\n```\n\n"
        "Return ONLY the full revised markdown prompt, no commentary, no code fences."
    )
    proposed = get_provider(cfg.llm).complete(meta).strip()
    if proposed.startswith("```"):
        proposed = proposed.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

    # Safety: never accept a degenerate rewrite that drops the contract.
    if "{{ profile }}" not in proposed or "{{ job_text }}" not in proposed or "HARD GATES" not in proposed:
        console.print("[yellow]Proposed rewrite dropped required parts — discarded for safety.[/]")
        return None

    if dry_run:
        console.print(f"[cyan]Proposed Recruteur revision ({len(proposed)} chars). "
                      f"Re-run with --apply to write it.[/]")
        return proposed

    backup = active.with_suffix(".md.bak")
    backup.write_text(current, encoding="utf-8")
    active.write_text(proposed, encoding="utf-8")
    console.print(f"[green]✓[/] Recruteur prompt updated (backup at {backup.name}).")
    return proposed
