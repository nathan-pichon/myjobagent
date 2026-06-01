"""Trieur (gatekeeper) agent — classifies a URL as a single job page or not.

Code-level fast-track / reject patterns bypass the LLM for obvious cases
(handled in engine.filters). This module is the LLM fallback for ambiguous URLs.
"""
from __future__ import annotations

from jobhunt.engine.prompts import render_prompt
from jobhunt.llm.base import LLMProvider
from jobhunt.util import extract_json


def is_single_job(llm: LLMProvider, url: str) -> bool:
    data = extract_json(llm.complete(render_prompt("trieur", url=url))) or {}
    return bool(data.get("is_single_job", False))
