"""Orchestration loop: refactor of the original run_autonomous_loop.

Two phases per step:
 1. Fast-path — if the URL queue is non-empty, pop & process one URL
    (filters → Trieur fast-track/LLM → scrape → Recruteur).
 2. Scout phase — if the queue is empty, ask the Scout for the next query.

Scrapers/filters are imported lazily so `validate`/`doctor` work without the
optional `scrape` extra installed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from rich.console import Console

from jobhunt.config import JobHuntConfig
from jobhunt.engine import recruteur, scout, trieur
from jobhunt.llm.base import get_provider
from jobhunt.sources import Offer
from jobhunt.store import Job, Store

console = Console()


@dataclass
class RunStats:
    steps: int = 0
    searches: int = 0
    urls_seen: int = 0
    matches: int = 0
    new_matches: list[dict] = field(default_factory=list)
    phase: str = "starting"        # human-readable current activity (live)
    last_match: dict | None = None  # most recent match, for the live feed


def _evaluate_offer(offer, text, llm, cfg, store, stats, threshold) -> None:
    """Score one offer's text and persist a match or a why-not rejection.

    `offer` may be a sources.Offer (with company/location/contract metadata) or
    None when only a URL+text are known.
    """
    url = offer.url
    if not text or len(text.strip()) < 100:
        store.record_rejection(url, "empty", "page vide ou trop courte")
        return
    if scrapers_is_expired(text):
        console.print(f"[dim]⏰ expired, skipping LLM: {url}[/]")
        store.record_rejection(url, "expired", "offre expirée / pourvue")
        return

    evaluation = recruteur.evaluate(llm, cfg, text)
    if evaluation["score"] >= threshold:
        # Prefer the source's structured metadata; fall back to the LLM's.
        job = Job(
            url=url,
            title=(offer.title or evaluation["title"]),
            company=(offer.company or evaluation["company"]),
            location=(offer.location or evaluation["location"]),
            contract=(offer.contract or evaluation["contract"]),
            score=evaluation["score"],
            breakdown=evaluation["breakdown"],
            summary=evaluation["summary"],
            source=offer.source or (url.split("/")[2] if "/" in url else url),
        )
        is_new = store.upsert_job(job)
        stats.matches += 1
        if is_new:
            stats.new_matches.append(evaluation)
            stats.last_match = {
                "title": job.title, "company": job.company,
                "score": job.score, "source": job.source,
            }
            console.print(
                f"  [green]✦ Match[/] {job.title} · {job.company} "
                f"· [bold]{evaluation['score']}/100[/] [dim]({job.source})[/]"
            )
    else:
        reason, detail = _rejection_reason(evaluation, threshold)
        store.record_rejection(url, reason, detail, score=evaluation["score"])


def scrapers_is_expired(text: str) -> bool:
    from jobhunt.engine import scrapers

    return scrapers.is_expired(text)


def _rejection_reason(evaluation: dict, threshold: int) -> tuple[str, str]:
    """Infer the dominant 'why-not' reason from a sub-threshold evaluation,
    so the user understands what was filtered and can tune their criteria."""
    bd = evaluation.get("breakdown", {})
    score = evaluation.get("score", 0)

    def _ratio(key: str) -> float:
        seg = bd.get(key, {})
        mx = seg.get("max", 1) or 1
        return seg.get("score", 0) / mx

    if _ratio("location") == 0:
        return "location", f"lieu hors zone (score {score})"
    if _ratio("stack") <= 0.25:
        return "stack", f"stack hors cible (score {score})"
    if _ratio("role") <= 0.25:
        return "role", f"rôle/séniorité non aligné (score {score})"
    return "below_threshold", f"score {score} < {threshold}"


def run(cfg: JobHuntConfig, store: Store, *, max_steps: int | None = None,
        on_progress=None) -> RunStats:
    """Run a hunt. `on_progress(stats)` is called after each meaningful step so a
    live dashboard can reflect progress in real time (it reads the same SQLite
    the loop writes to, so it always sees the latest matches)."""
    from jobhunt.engine import filters, scrapers  # lazy: needs `scrape` extra
    from jobhunt.sources import get_sources

    def _tick(phase: str) -> None:
        stats.phase = phase
        if on_progress:
            try:
                on_progress(stats)
            except Exception:  # noqa: BLE001  (a UI hook must never break the hunt)
                pass

    llm = get_provider(cfg.llm)
    stats = RunStats()
    started = time.time()
    max_steps = max_steps or cfg.search.max_steps
    threshold = cfg.scoring.threshold

    # Build & report enabled sources (official first, web fallback last).
    sources = get_sources(cfg)
    active = []
    for src in sources:
        ok, msg = src.available(cfg)
        if ok:
            active.append(src)
            console.print(f"  [green]source[/] {src.name} — {msg}")
        else:
            console.print(f"  [dim]source {src.name} off — {msg}[/]")
    if not active:
        console.print("[red]No usable source. Enable France Travail or install the scrape extra.[/]")
        return stats

    queue: list[str] = []  # URL-only offers awaiting scraping
    mode_idx = 0
    platform_idx = 0
    last_error = ""

    for step in range(max_steps):
        stats.steps = step + 1

        # ---- Phase 1: scrape queued URL-only offers ---------------------- #
        if queue:
            queue = filters.prioritize_platform_urls(queue, cfg.search.platforms)
            url = queue.pop(0)
            if store.is_visited(url):
                continue
            store.mark_visited(url)
            stats.urls_seen += 1

            _tick(f"Analyse de {_domain(url)} ({len(queue)} en file)")
            if not filters.is_fasttrack_job_url(url, cfg.filters.fasttrack_job_patterns):
                if not trieur.is_single_job(llm, url):
                    continue
            try:
                text = scrapers.extract_text(url)
            except Exception as e:  # noqa: BLE001
                console.print(f"[yellow]extract failed[/]: {url} ({e})")
                continue
            _evaluate_offer(Offer(url=url, source=_domain(url)), text, llm, cfg, store, stats, threshold)
            _tick(f"{stats.matches} matches · {len(queue)} en file")
            continue

        # ---- Phase 2: Scout generates the next query --------------------- #
        mode = cfg.search.modes[mode_idx % len(cfg.search.modes)]
        mode_idx += 1
        next_platform = (
            cfg.search.platforms[platform_idx % len(cfg.search.platforms)]
            if cfg.search.platforms else ""
        )
        platform_idx += 1

        decision = scout.run_scout(
            llm, cfg,
            search_mode=mode,
            next_platform=next_platform,
            recent_searches=store.recent_searches(),
            visited_count=store.visited_count(),
            queue_count=len(queue),
            error=last_error,
        )
        last_error = ""
        if decision.action == "STOP":
            console.print("[cyan]Scout signalled STOP — search space exhausted.[/]")
            break
        if not decision.query:
            last_error = "Scout returned an empty query."
            continue

        store.mark_search(decision.query)
        stats.searches += 1
        console.print(f"  [blue]Scout[/] ▸ {decision.query}")
        _tick(f"Recherche : {decision.query[:60]}")

        # ---- Query every active source. Offers WITH text are scored now
        #      (no scraping); URL-only offers are queued for scraping. ------ #
        url_only = 0
        for src in active:
            try:
                offers = list(src.fetch(cfg, decision.query, cfg.search.max_results_per_query))
            except Exception as e:  # noqa: BLE001
                console.print(f"  [yellow]source {src.name} failed[/]: {e}")
                last_error = f"{src.name} failed: {e}"
                continue
            for off in offers:
                if not off.url or store.is_visited(off.url):
                    continue
                if filters.is_blacklisted_domain(off.url, cfg.filters.domain_blacklist):
                    continue
                if off.has_text:
                    # structured/official offer → score directly, mark visited
                    store.mark_visited(off.url)
                    stats.urls_seen += 1
                    _evaluate_offer(off, off.text, llm, cfg, store, stats, threshold)
                    _tick(f"{src.name} · {stats.matches} matches")
                else:
                    if off.url not in queue and not filters.has_reject_pattern(
                        off.url, cfg.filters.reject_url_patterns
                    ):
                        queue.append(off.url)
                        url_only += 1
            console.print(f"  [dim]{src.name}: {len(offers)} offers[/]")
        console.print(f"  [dim]→ {url_only} queued for scraping[/]")

    store.record_run(started, stats.steps, stats.urls_seen, stats.matches, {"searches": stats.searches})
    return stats


def _domain(url: str) -> str:
    return url.split("/")[2] if "://" in url and len(url.split("/")) > 2 else url
