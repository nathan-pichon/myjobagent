"""Digest — the daily retention loop. After a hunt, summarise what's NEW and
worth the user's attention. Local-only; optional desktop notification.

This is the "l'agent a bossé cette nuit, voici 3 offres ≥ 80" moment the
reviews flagged as the #1 retention driver.
"""
from __future__ import annotations

import subprocess
import sys

from rich.console import Console

from jobhunt.config import JobHuntConfig
from jobhunt.store import Store

console = Console()


def build_digest(new_matches: list[dict], cfg: JobHuntConfig, high_bar: int = 75) -> str:
    """Render a short, calm digest of the new matches (verdict-first)."""
    if not new_matches:
        return "Aucune nouvelle offre cette fois. Ton agent continue de veiller."
    top = sorted(new_matches, key=lambda m: m.get("score", 0), reverse=True)
    strong = [m for m in top if m.get("score", 0) >= high_bar]
    head = (
        f"{len(strong)} nouvelle(s) offre(s) ≥ {high_bar} ce matin"
        if strong else f"{len(top)} nouvelle(s) offre(s) à regarder"
    )
    lines = [head]
    for m in top[:5]:
        lines.append(
            f"  • {m.get('score',0):>3} · {m.get('title','?')} — {m.get('company','?')} ({m.get('location','')})"
        )
    if len(top) > 5:
        lines.append(f"  … et {len(top) - 5} autre(s).")
    return "\n".join(lines)


def notify_os(title: str, message: str) -> None:
    """Best-effort native desktop notification. Silent on failure (headless/CI)."""
    try:
        if sys.platform == "darwin":
            safe = message.replace('"', "'")[:200]
            subprocess.run(
                ["osascript", "-e", f'display notification "{safe}" with title "{title}"'],
                check=False, capture_output=True, timeout=5,
            )
        elif sys.platform.startswith("linux"):
            subprocess.run(["notify-send", title, message[:200]], check=False, capture_output=True, timeout=5)
        # Windows: skipped (would need a toast lib); the CLI prints the digest anyway.
    except Exception:  # noqa: BLE001
        pass


def print_digest(new_matches: list[dict], cfg: JobHuntConfig, *, notify: bool = True) -> str:
    text = build_digest(new_matches, cfg)
    console.print(f"\n[bold]🔦 Digest MyJobAgent[/]\n{text}\n")
    if notify and new_matches:
        notify_os("MyJobAgent", build_digest(new_matches, cfg).splitlines()[0])
    return text
