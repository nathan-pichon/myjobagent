"""Recruteur agent — scores a job posting against the profile with an
explainable, typed breakdown (the product's signature)."""
from __future__ import annotations

from typing import Any

from jobhunt.config import JobHuntConfig
from jobhunt.engine.prompts import render_prompt
from jobhunt.llm.base import LLMProvider
from jobhunt.util import clamp_int, extract_json

_EMPTY_BREAKDOWN = {
    "stack": {"score": 0, "max": 40, "matched": [], "gaps": []},
    "role": {"score": 0, "max": 20, "matched": [], "gaps": []},
    "location": {"score": 0, "max": 25, "matched": [], "gaps": []},
    "contract": {"score": 0, "max": 15, "matched": [], "gaps": []},
}


def _verdict(score: int) -> str:
    if score >= 75:
        return "strong"
    if score >= 60:
        return "good"
    if score >= 50:
        return "partial"
    return "weak"


def evaluate(llm: LLMProvider, cfg: JobHuntConfig, job_text: str) -> dict[str, Any]:
    """Return a normalised evaluation dict. Never raises on bad model output."""
    raw = llm.complete(
        render_prompt("recruteur", profile=cfg.profile.as_prompt_text(), job_text=job_text[:5000])
    )
    data = extract_json(raw) or {}

    score = clamp_int(data.get("score"), 0, 100, default=0)
    breakdown = data.get("breakdown") if isinstance(data.get("breakdown"), dict) else {}
    norm_breakdown = {}
    maxes = {"stack": 40, "role": 20, "location": 25, "contract": 15}
    for key, mx in maxes.items():
        seg = breakdown.get(key, {}) if isinstance(breakdown.get(key), dict) else {}
        norm_breakdown[key] = {
            "score": clamp_int(seg.get("score"), 0, mx, default=0),
            "max": mx,
            "matched": seg.get("matched", []) if isinstance(seg.get("matched"), list) else [],
            "gaps": [g for g in seg.get("gaps", []) if isinstance(g, dict)] if isinstance(seg.get("gaps"), list) else [],
        }

    return {
        "score": score,
        "verdict": data.get("verdict") or _verdict(score),
        "title": str(data.get("title") or "Sans titre"),
        "company": str(data.get("company") or "Inconnue"),
        "location": str(data.get("location") or ""),
        "contract": str(data.get("contract") or ""),
        "summary": str(data.get("summary") or ""),
        "breakdown": norm_breakdown or dict(_EMPTY_BREAKDOWN),
    }
