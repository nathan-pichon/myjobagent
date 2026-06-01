"""Jinja2 prompt loading from the packaged `jobhunt/prompts/` templates."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Template

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=None)
def _template_source(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template missing: {path}")
    return path.read_text(encoding="utf-8")


def render_prompt(name: str, **variables) -> str:
    return Template(_template_source(name)).render(**variables)
