"""Web search source (DuckDuckGo via ddgs) — the broad fallback.

Yields URL-only offers (no inline text → the engine scrapes them). Adds
retry-with-backoff so a transient rate-limit doesn't kill the run.
"""
from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING, Iterator

from jobhunt.sources.base import Offer

if TYPE_CHECKING:
    from jobhunt.config import JobHuntConfig


class WebSearchSource:
    name = "web"

    def available(self, cfg: "JobHuntConfig") -> tuple[bool, str]:
        try:
            import ddgs  # noqa: F401
        except ImportError:
            return False, "Web search: install the scrape extra (pip install 'jobhunt[scrape]')"
        return True, "Web search (DuckDuckGo) available"

    def fetch(self, cfg: "JobHuntConfig", query: str, limit: int) -> Iterator[Offer]:
        from jobhunt.engine import scrapers

        urls: list[str] = []
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                urls = scrapers.search_web(query, limit)
                break
            except Exception as e:  # noqa: BLE001  (ddgs raises various types)
                last_err = e
                time.sleep((2 ** attempt) + random.uniform(0, 1))
        if not urls and last_err is not None:
            raise RuntimeError(f"web search failed after retries: {last_err}")
        for u in urls:
            yield Offer(url=u, source="web")
