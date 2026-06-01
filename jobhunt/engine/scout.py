"""Scout agent — generates the next search query (or STOP)."""
from __future__ import annotations

from dataclasses import dataclass

from jobhunt.config import JobHuntConfig
from jobhunt.engine.prompts import render_prompt
from jobhunt.llm.base import LLMProvider
from jobhunt.util import extract_json


@dataclass
class ScoutDecision:
    action: str  # "SEARCH" | "STOP"
    query: str
    thought: str = ""


def run_scout(
    llm: LLMProvider,
    cfg: JobHuntConfig,
    *,
    search_mode: str,
    next_platform: str,
    recent_searches: list[str],
    visited_count: int,
    queue_count: int,
    error: str = "",
) -> ScoutDecision:
    prompt = render_prompt(
        "scout",
        profile=cfg.profile.as_prompt_text(),
        platforms=", ".join(cfg.search.platforms),
        recent_searches=recent_searches,
        visited_count=visited_count,
        queue_count=queue_count,
        error=error,
        search_mode=search_mode,
        next_platform=next_platform,
    )
    data = extract_json(llm.complete(prompt)) or {}
    action = str(data.get("action", "STOP")).upper()
    if action not in ("SEARCH", "STOP"):
        action = "STOP"
    return ScoutDecision(
        action=action,
        query=str(data.get("parameter", "")).strip(),
        thought=str(data.get("thought", "")),
    )
