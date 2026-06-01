"""Code-level URL filtering — runs before any LLM call.

Pulls its pattern lists from the JobHuntConfig so nothing is hardcoded.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jobhunt.config import JobHuntConfig
    from jobhunt.store import Store


def is_blacklisted_domain(url: str, blacklist: list[str]) -> bool:
    low = url.lower()
    return any(domain in low for domain in blacklist)


def has_reject_pattern(url: str, patterns: list[str]) -> bool:
    low = url.lower()
    return any(p in low for p in patterns)


def is_fasttrack_job_url(url: str, patterns: list[str]) -> bool:
    """True if the URL clearly points to a single posting (has content after
    the job-path segment), so we can skip the Trieur LLM."""
    low = url.lower()
    for pattern in patterns:
        idx = low.find(pattern)
        if idx != -1:
            after = low[idx + len(pattern):]
            if after and after.strip("/"):
                return True
    return False


def filter_urls(urls: list[str], store: "Store", queue: list[str], cfg: "JobHuntConfig") -> list[str]:
    """Keep only unseen, non-blacklisted, non-rejected URLs."""
    out: list[str] = []
    seen = set(queue)
    for url in urls:
        if not url or url in seen or store.is_visited(url):
            continue
        if is_blacklisted_domain(url, cfg.filters.domain_blacklist):
            continue
        if has_reject_pattern(url, cfg.filters.reject_url_patterns):
            continue
        # Respect source toggles (LinkedIn off by default).
        low = url.lower()
        if "linkedin.com" in low and not cfg.sources.linkedin_enabled:
            continue
        if "indeed." in low and not cfg.sources.indeed_enabled:
            continue
        out.append(url)
        seen.add(url)
    return out


def prioritize_platform_urls(queue: list[str], platforms: list[str]) -> list[str]:
    platform_urls, other = [], []
    for url in queue:
        low = url.lower()
        (platform_urls if any(p in low for p in platforms) else other).append(url)
    return platform_urls + other
