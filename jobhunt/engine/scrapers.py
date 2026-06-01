"""Web search + page extraction. Imported lazily by the loop so the rest of
the package works without the optional `scrape` extra.

Refactor of utils/browser_scrapers.py: DuckDuckGo (ddgs) for search,
Playwright + stealth for extraction, with noise-stripping and truncation.
"""
from __future__ import annotations

import random
import time

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

NOISE_SELECTORS = [
    "nav", "header", "footer", "aside",
    "[class*='cookie']", "[class*='Cookie']", "[id*='cookie']",
    "[class*='consent']", "[class*='banner']", "[class*='sidebar']",
    "[class*='menu']", "[class*='social']", "[class*='share']",
    "[class*='newsletter']", "[class*='popup']", "[class*='modal']",
    "[class*='gdpr']", "[class*='advert']", "[class*='ad-']",
    "[class*='related']", "[class*='recommend']", "[class*='similar']",
    "script", "style", "noscript", "iframe", "svg",
]

MAIN_CONTENT_SELECTORS = [
    "main", "article", "[role='main']",
    ".job-description", ".job-content", ".offer-content", ".job-details",
    ".posting-content", ".vacancy-content", ".description",
    ".annonce-content", ".mission-detail",
    "[class*='jobDescription']", "[class*='job-description']",
    "[class*='offer-detail']", "[class*='mission-detail']",
    "[data-testid='job-description']",
    "#job-description", "#job-content", "#description",
]

EXPIRED_MARKERS = [
    "this position is no longer available", "no longer accepting applications",
    "this job is no longer available", "position has been filled", "position filled",
    "offer expired", "offer has expired", "offre pourvue", "offre expirée",
    "offre expiree", "candidatures closes", "candidatures fermées",
    "ce poste n'est plus disponible", "cette offre n'est plus disponible",
    "annonce désactivée", "annonce desactivee", "cette offre a expiré",
    "les candidatures ne sont plus acceptées",
]


def search_web(query: str, max_results: int = 25) -> list[str]:
    from ddgs import DDGS

    urls: list[str] = []

    def _run(q: str) -> None:
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(q, max_results=max_results):
                    href = r.get("href")
                    if href and href not in urls:
                        urls.append(href)
        except Exception as e:  # noqa: BLE001
            print(f"[ddgs] search error: {e}")

    _run(query)
    if not urls and "site:" in query:
        domain = query.split("site:")[1].split()[0]
        _run(query.replace(f"site:{domain}", domain))
    return urls


def is_expired(text: str) -> bool:
    low = text.lower()
    return any(m in low for m in EXPIRED_MARKERS)


def extract_text(url: str, max_chars: int = 5000) -> str:
    from playwright.sync_api import sync_playwright

    try:
        from playwright_stealth import Stealth
    except ImportError:
        Stealth = None  # type: ignore

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="fr-FR",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()
        if Stealth is not None:
            try:
                Stealth().apply_stealth_sync(page)
            except Exception:  # noqa: BLE001
                pass
        try:
            time.sleep(random.uniform(1.0, 2.5))
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)
            _strip_noise(page)
            raw = _main_content(page)
            return _clean(raw, max_chars) if raw else ""
        except Exception as e:  # noqa: BLE001
            print(f"[playwright] extract error on {url}: {e}")
            return ""
        finally:
            context.close()
            browser.close()


def _strip_noise(page) -> None:
    js = """(() => { const s = %s; s.forEach(sel => { try {
        document.querySelectorAll(sel).forEach(el => el.remove()); } catch(e){} }); })()""" % (
        str(NOISE_SELECTORS).replace("'", '"')
    )
    try:
        page.evaluate(js)
    except Exception:  # noqa: BLE001
        pass


def _main_content(page) -> str:
    for sel in MAIN_CONTENT_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 200:
                    return text
        except Exception:  # noqa: BLE001
            continue
    body = page.query_selector("body")
    return body.inner_text().strip() if body else ""


def _clean(text: str, max_chars: int) -> str:
    lines, prev = [], None
    for line in text.splitlines():
        s = line.strip()
        if s and len(s) > 2 and s != prev:
            lines.append(s)
            prev = s
    out = "\n".join(lines)
    return out[:max_chars] + "\n[...truncated...]" if len(out) > max_chars else out
