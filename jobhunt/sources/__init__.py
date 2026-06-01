"""Sourcing layer — pluggable job sources, robust by design.

Each source yields `Offer`s. An offer may carry its description text already
(structured/official APIs like France Travail) → no scraping needed, or only a
URL (web search) → the engine scrapes it.

Priority order: official/structured sources first (reliable, legal, text inline),
web search as a broad fallback. This is the fix for the "everything depends on
DuckDuckGo" fragility.
"""
from jobhunt.sources.base import Offer, Source, get_sources

__all__ = ["Offer", "Source", "get_sources"]
