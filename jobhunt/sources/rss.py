"""RSS / Atom recruitment feeds — the most robust source there is.

Official, legal, stable for years, and entries usually ship the full job
description → no scraping needed (like France Travail).

Design notes:
 * A feed is a fixed list of recent postings, NOT a keyword search. So we fetch
   each feed ONCE per run (cached), then filter entries locally by the query
   keywords. This avoids hammering feeds on every Scout query.
 * Pure stdlib parsing (xml.etree) — handles RSS 2.0 and Atom. No feedparser
   dependency, keeps the install light.
 * HTML is stripped from descriptions to feed the Recruteur clean text.
"""
from __future__ import annotations

import html as _html
import re
import urllib.request
from email.utils import parsedate_to_datetime
from typing import TYPE_CHECKING, Iterator
from xml.etree import ElementTree as ET

from jobhunt.sources.base import Offer

if TYPE_CHECKING:
    from jobhunt.config import JobHuntConfig, RssFeed

_UA = "MyJobAgent/0.1 (+local job-hunting agent)"
_ATOM = "{http://www.w3.org/2005/Atom}"

# Default recruitment feeds, pre-filled into a fresh config so the user SEES
# them and can remove/add any from the local dashboard. These are stable public
# RSS/Atom endpoints (remote-friendly tech + EU). The user owns the list.
DEFAULT_FEEDS = [
    {"name": "WeWorkRemotely — Backend",
     "url": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"},
    {"name": "WeWorkRemotely — Full-Stack",
     "url": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss"},
    {"name": "Remotive — Software Dev",
     "url": "https://remotive.com/remote-jobs/feed/software-dev"},
    {"name": "RemoteOK",
     "url": "https://remoteok.com/remote-dev-jobs.rss"},
    {"name": "Himalayas — Software",
     "url": "https://himalayas.app/jobs/rss?category=software-engineering"},
]


def default_feeds() -> list[dict]:
    """A fresh copy of the default feed list (name/url/enabled)."""
    return [{"name": f["name"], "url": f["url"], "enabled": True} for f in DEFAULT_FEEDS]


class RssSource:
    name = "rss"

    def __init__(self) -> None:
        self._cache: dict[str, list[Offer]] = {}  # feed url -> parsed offers

    def available(self, cfg: "JobHuntConfig") -> tuple[bool, str]:
        feeds = _feeds(cfg)
        if not feeds:
            return False, "RSS: aucun flux (ajoute-en dans ⚙ Réglages ou restaure les flux par défaut)"
        return True, f"RSS: {len(feeds)} flux configuré(s)"

    def fetch(self, cfg: "JobHuntConfig", query: str, limit: int) -> Iterator[Offer]:
        terms = _keywords(query)
        for feed in _feeds(cfg):
            offers = self._cache.get(feed.url)
            if offers is None:
                try:
                    offers = _parse_feed(feed.url, feed.name)
                except Exception as e:  # noqa: BLE001
                    # one bad feed shouldn't kill the source
                    print(f"[rss] feed '{feed.name}' failed: {e}")
                    offers = []
                self._cache[feed.url] = offers
            matched = 0
            for off in offers:
                if matched >= limit:
                    break
                if _matches(off, terms):
                    matched += 1
                    yield off


def _feeds(cfg: "JobHuntConfig") -> list["RssFeed"]:
    # The user owns the list (pre-filled with DEFAULT_FEEDS in default_config()).
    # An empty list means they removed them all on purpose — respect that.
    if not cfg.sources.rss_enabled:
        return []
    return [f for f in cfg.sources.rss_feeds if f.enabled]


def _keywords(query: str) -> list[str]:
    q = " ".join(p for p in query.split() if not p.startswith("site:"))
    # keep alphanumeric tokens of length >= 3, lowercased
    return [t for t in re.findall(r"[a-zA-Z0-9.+#]+", q.lower()) if len(t) >= 3]


def _matches(off: Offer, terms: list[str]) -> bool:
    """Loose OR-match: at least one query term appears in title/text. The
    Recruteur does the precise scoring afterwards; here we just pre-filter."""
    if not terms:
        return True
    hay = f"{off.title} {off.text} {off.location}".lower()
    return any(t in hay for t in terms)


def _strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    return re.sub(r"[ \t]+", " ", s).strip()


def _parse_feed(url: str, feed_name: str) -> list[Offer]:
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)

    offers: list[Offer] = []
    # RSS 2.0: <channel><item>...   Atom: <feed><entry>...
    items = root.findall(".//item")
    if items:
        for it in items:
            offers.append(_rss_item(it, feed_name))
    else:
        for en in root.findall(f"{_ATOM}entry"):
            offers.append(_atom_entry(en, feed_name))
    return offers


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _rss_item(it, feed_name: str) -> Offer:
    title = _text(it.find("title"))
    link = _text(it.find("link"))
    desc = _text(it.find("description"))
    # common extensions: <content:encoded>, <dc:creator>, <category>
    content = it.find("{http://purl.org/rss/1.0/modules/content/}encoded")
    if content is not None and _text(content):
        desc = _text(content)
    creator = it.find("{http://purl.org/dc/elements/1.1/}creator")
    company = _text(creator)
    pub = _text(it.find("pubDate"))
    posted = _iso(pub)
    return Offer(
        url=link,
        title=title,
        company=company,
        text=_strip_html(desc),
        source=f"rss:{feed_name}",
        posted_at=posted,
    )


def _atom_entry(en, feed_name: str) -> Offer:
    title = _text(en.find(f"{_ATOM}title"))
    link_el = en.find(f"{_ATOM}link")
    link = link_el.get("href") if link_el is not None else ""
    summary = _text(en.find(f"{_ATOM}summary")) or _text(en.find(f"{_ATOM}content"))
    updated = _text(en.find(f"{_ATOM}updated")) or _text(en.find(f"{_ATOM}published"))
    return Offer(
        url=link,
        title=title,
        text=_strip_html(summary),
        source=f"rss:{feed_name}",
        posted_at=updated,
    )


def _iso(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        return parsedate_to_datetime(date_str).isoformat()
    except (TypeError, ValueError):
        return date_str
