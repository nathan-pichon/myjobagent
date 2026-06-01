"""Source abstraction + registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    from jobhunt.config import JobHuntConfig


@dataclass
class Offer:
    """A job offer from a source.

    If `text` is set, it's the full description (no scraping needed). Otherwise
    only `url` is known and the engine will fetch the page.
    """
    url: str
    title: str = ""
    company: str = ""
    location: str = ""
    contract: str = ""
    text: str = ""           # full description if the source provides it
    source: str = ""         # source name (e.g. "france-travail", "web")
    posted_at: str = ""      # ISO date if known (freshness)
    extra: dict = field(default_factory=dict)

    @property
    def has_text(self) -> bool:
        return bool(self.text and len(self.text.strip()) >= 100)


@runtime_checkable
class Source(Protocol):
    name: str

    def available(self, cfg: "JobHuntConfig") -> tuple[bool, str]:
        """Return (usable, message) — e.g. credentials present, deps installed."""
        ...

    def fetch(self, cfg: "JobHuntConfig", query: str, limit: int) -> Iterator[Offer]:
        """Yield offers for a query."""
        ...


def get_sources(cfg: "JobHuntConfig") -> list["Source"]:
    """Build the ordered list of enabled sources (official first, web last)."""
    sources: list[Source] = []
    if cfg.sources.france_travail_enabled:
        from jobhunt.sources.france_travail import FranceTravailSource

        sources.append(FranceTravailSource())
    if cfg.sources.rss_enabled:
        from jobhunt.sources.rss import RssSource

        sources.append(RssSource())
    # Web search (DuckDuckGo) is the broad fallback, always last.
    from jobhunt.sources.web_search import WebSearchSource

    sources.append(WebSearchSource())
    return sources
