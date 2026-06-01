"""Offline unit tests (no network, no LLM). Run: pytest -q"""
from pathlib import Path

import pytest

from jobhunt.config import JobHuntConfig, default_config, load_config_b64, ConfigError
from jobhunt.engine import filters, recruteur
from jobhunt.store import Job, Store
from jobhunt.util import clamp_int, extract_json


class FakeLLM:
    def __init__(self, payload: str):
        self.payload = payload

    def complete(self, prompt: str) -> str:
        return self.payload

    def health(self):
        return (True, "ok")


def test_extract_json_handles_fences_and_noise():
    assert extract_json('```json\n{"a":1}\n```') == {"a": 1}
    assert extract_json('Sure! {"action":"SEARCH"} ok')["action"] == "SEARCH"
    assert extract_json("not json") is None


def test_clamp_int():
    assert clamp_int("45", 0, 40) == 40
    assert clamp_int(None, 0, 40, 7) == 7
    assert clamp_int(-3, 0, 40) == 0


def test_fasttrack_and_reject_patterns():
    cfg = default_config()
    assert filters.is_fasttrack_job_url("https://x.com/offre/dev-backend-123", cfg.filters.fasttrack_job_patterns)
    assert not filters.is_fasttrack_job_url("https://x.com/offres/", cfg.filters.fasttrack_job_patterns)
    assert filters.has_reject_pattern("https://x.com/blog/article", cfg.filters.reject_url_patterns)
    assert filters.is_blacklisted_domain("https://reddit.com/r/jobs", cfg.filters.domain_blacklist)


def test_store_dedup_and_feedback(tmp_path: Path):
    db = str(tmp_path / "t.db")
    s = Store(db)
    a = Job(url="https://a.com/job/1", title="Senior Backend", company="Acme", location="Nice", score=82, source="a.com")
    b = Job(url="https://b.com/job/9", title="senior  backend", company="ACME", location="nice ", score=80, source="b.com")
    assert s.upsert_job(a) is True
    assert s.upsert_job(b) is False  # merged via dedup_key
    jobs = s.get_jobs(min_score=50)
    assert len(jobs) == 1
    assert len(jobs[0]["sources"]) == 2
    s.set_feedback("https://a.com/job/1", 1)
    assert s.quality_stats()["up"] == 1
    s.set_status("https://a.com/job/1", "applied")
    assert len(s.get_jobs(status="applied")) == 1
    with pytest.raises(ValueError):
        s.set_status("https://a.com/job/1", "bogus")
    s.close()


def test_recruteur_clamps_bad_model_output():
    payload = '{"score":150,"title":"X","breakdown":{"stack":{"score":99,"max":40,"matched":[],"gaps":[]}}}'
    ev = recruteur.evaluate(FakeLLM(payload), default_config(), "job text " * 40)
    assert ev["score"] == 100
    assert ev["breakdown"]["stack"]["score"] == 40
    assert ev["verdict"] == "strong"


def test_recruteur_survives_garbage_output():
    ev = recruteur.evaluate(FakeLLM("the model said no"), default_config(), "x")
    assert ev["score"] == 0
    assert ev["verdict"] == "weak"
    assert set(ev["breakdown"]) == {"stack", "role", "location", "contract"}


def test_config_b64_roundtrip():
    import base64

    cfg = default_config()
    raw = cfg.model_dump_json().encode()
    b64 = base64.urlsafe_b64encode(raw).decode()
    loaded = load_config_b64(b64)
    assert isinstance(loaded, JobHuntConfig)
    assert loaded.profile.roles == cfg.profile.roles
    with pytest.raises(ConfigError):
        load_config_b64("!!!notbase64!!!")


def test_rejection_reason_inference():
    from jobhunt.engine.loop import _rejection_reason

    loc = {"score": 40, "breakdown": {"location": {"score": 0, "max": 25},
           "stack": {"score": 40, "max": 40}, "role": {"score": 20, "max": 20}}}
    assert _rejection_reason(loc, 50)[0] == "location"
    stack = {"score": 30, "breakdown": {"location": {"score": 25, "max": 25},
             "stack": {"score": 6, "max": 40}, "role": {"score": 20, "max": 20}}}
    assert _rejection_reason(stack, 50)[0] == "stack"
    low = {"score": 47, "breakdown": {"location": {"score": 20, "max": 25},
           "stack": {"score": 30, "max": 40}, "role": {"score": 14, "max": 20}}}
    assert _rejection_reason(low, 50)[0] == "below_threshold"


def test_store_rejections(tmp_path: Path):
    s = Store(str(tmp_path / "t.db"))
    s.record_rejection("https://x.com/go", "stack", "off-stack", 35)
    s.record_rejection("https://y.com/paris", "location", "wrong city", 40)
    assert s.rejection_summary() == {"stack": 1, "location": 1}
    assert len(s.get_rejections()) == 2
    s.close()


def test_dashboard_shows_whynot(tmp_path: Path):
    from jobhunt.dashboard.render import render

    s = Store(str(tmp_path / "t.db"))
    s.upsert_job(Job(url="https://a.com/job/1", title="Senior Backend", company="Acme",
                     location="Nice", score=82, source="a.com"))
    s.record_rejection("https://y.com/paris", "location", "lieu hors zone", 40)
    out = render(s, default_config(), tmp_path / "d.html")
    txt = out.read_text()
    assert "Pourquoi pas" in txt and "Lieu hors zone" in txt
    s.close()


def test_dashboard_kanban(tmp_path: Path):
    from jobhunt.dashboard.render import render

    s = Store(str(tmp_path / "t.db"))
    s.upsert_job(Job(url="https://a.com/1", title="Senior Backend", company="Acme",
                     location="Nice", score=82, source="a.com"))
    s.upsert_job(Job(url="https://b.com/2", title="Tech Lead", company="Beta",
                     location="Remote", score=77, source="b.com"))
    s.set_status("https://b.com/2", "interested")
    out = render(s, default_config(), tmp_path / "d.html")
    h = out.read_text()
    assert "Pipeline de candidatures" in h
    assert 'mja move' in h
    assert "Intéressé" in h and "Trouvé" in h
    assert 'aria-live' in h
    assert h.count('class="kbn-col"') == 6
    s.close()


def test_source_ordering_and_offer_mapping():
    from jobhunt.sources import Offer, get_sources
    from jobhunt.sources.france_travail import _keywords, _to_offer

    cfg = default_config()
    cfg.sources.rss_enabled = False  # focus this test on FT + web ordering
    # official source first, web fallback last
    assert [s.name for s in get_sources(cfg)] == ["france-travail", "web"]
    # disabling FT leaves only web
    cfg.sources.france_travail_enabled = False
    assert [s.name for s in get_sources(cfg)] == ["web"]

    # FT payload → Offer with inline text (no scraping needed)
    off = _to_offer({
        "id": "X1", "intitule": "Backend Node.js", "description": "d" * 200,
        "lieuTravail": {"libelle": "06 - NICE"}, "entreprise": {"nom": "ACME"},
        "typeContratLibelle": "CDI", "dateCreation": "2026-05-30T10:00:00.000Z",
        "origineOffre": {"urlOrigine": "https://candidat.francetravail.fr/offres/detail/X1"},
    })
    assert off.has_text and off.company == "ACME" and off.contract == "CDI"
    assert off.source == "france-travail"
    assert _keywords("site:linkedin.com backend node") == "backend node"

    # an Offer without text is not "has_text"
    assert not Offer(url="https://x.com/1", source="web").has_text


def test_rss_parsing_and_filter():
    import xml.etree.ElementTree as ET

    from jobhunt.sources import rss

    rss20 = b"""<?xml version="1.0"?>
    <rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"
         xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
    <item><title>Senior Backend Engineer Node.js</title><link>https://f/1</link>
      <content:encoded><![CDATA[<p>We need a <b>Node.js</b> &amp; TypeScript expert. Remote France. Docker, PostgreSQL, microservices, 5+ years.</p>]]></content:encoded>
      <dc:creator>ACME Corp</dc:creator>
      <pubDate>Wed, 28 May 2026 09:00:00 +0000</pubDate></item>
    <item><title>Marketing Manager</title><link>https://f/2</link>
      <description>Growth and advertising</description></item>
    </channel></rss>"""
    items = ET.fromstring(rss20).findall(".//item")
    offers = [rss._rss_item(it, "Test") for it in items]
    o = offers[0]
    assert o.company == "ACME Corp" and o.source == "rss:Test"
    assert "Node.js" in o.text and "<b>" not in o.text and "& TypeScript" in o.text
    assert o.posted_at.startswith("2026-05-28")

    # Atom
    atom = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
    <entry><title>Tech Lead Backend</title><link href="https://a/9"/>
      <summary>Lead a backend team with Node.js and Kubernetes.</summary>
      <updated>2026-05-29T10:00:00Z</updated></entry></feed>"""
    a = [rss._atom_entry(e, "Atom") for e in ET.fromstring(atom).findall(rss._ATOM + "entry")][0]
    assert a.title == "Tech Lead Backend" and a.url.endswith("/9") and "Kubernetes" in a.text

    # keyword pre-filter (Recruteur does precise scoring later)
    terms = rss._keywords("site:x.com backend node typescript")
    assert "backend" in terms and "x.com" not in " ".join(terms)
    assert rss._matches(o, terms) and not rss._matches(offers[1], rss._keywords("backend node"))


def test_default_config_ships_visible_rss_feeds():
    from jobhunt.sources.rss import RssSource, _feeds, default_feeds

    cfg = default_config()
    # defaults are pre-filled into the config (visible/editable), not a hidden fallback
    assert len(cfg.sources.rss_feeds) >= 3
    assert all(f.url.startswith("http") for f in cfg.sources.rss_feeds)
    assert default_feeds()  # fresh copies available for "restore"

    # user removes them all → respected (NOT re-injected)
    cfg.sources.rss_feeds = []
    assert _feeds(cfg) == []
    ok, _ = RssSource().available(cfg)
    assert ok is False

    # per-feed enable toggle works
    cfg2 = default_config()
    cfg2.sources.rss_feeds[0].enabled = False
    assert len(_feeds(cfg2)) == len(cfg2.sources.rss_feeds) - 1


def test_rss_source_registry_and_cache():
    from jobhunt.config import RssFeed, default_config
    from jobhunt.sources import get_sources
    from jobhunt.sources import rss as R
    from jobhunt.sources.base import Offer

    cfg = default_config()
    assert [s.name for s in get_sources(cfg)] == ["france-travail", "rss", "web"]
    cfg.sources.rss_enabled = False
    assert [s.name for s in get_sources(cfg)] == ["france-travail", "web"]

    # fetch filters by keyword; feed parsed once across queries (cache)
    long_text = ("Senior Backend Engineer role. We need Node.js and TypeScript expertise "
                 "to build scalable APIs. Remote from France, CDI, 5+ years of experience. "
                 "Stack includes Docker, PostgreSQL, Kubernetes and microservices.")
    sample = [
        Offer(url="https://f/1", title="Senior Backend Node.js", text=long_text, source="rss:T"),
        Offer(url="https://f/2", title="Marketing Manager", text="Growth marketing role in Paris office.", source="rss:T"),
    ]
    calls = [0]

    def fake(url, name):
        calls[0] += 1
        return list(sample)

    R._parse_feed = fake
    cfg2 = default_config()
    cfg2.sources.rss_feeds = [RssFeed(name="T", url="https://feed/rss")]
    src = R.RssSource()
    got = list(src.fetch(cfg2, "backend node typescript", 25))
    assert len(got) == 1 and got[0].has_text
    list(src.fetch(cfg2, "marketing", 25))
    assert calls[0] == 1  # cached across queries


def test_france_travail_disabled_without_credentials(monkeypatch):
    from jobhunt.sources.france_travail import FranceTravailSource

    monkeypatch.delenv("FRANCE_TRAVAIL_CLIENT_ID", raising=False)
    monkeypatch.delenv("FRANCE_TRAVAIL_CLIENT_SECRET", raising=False)
    ok, msg = FranceTravailSource().available(default_config())
    assert ok is False and "FRANCE_TRAVAIL_CLIENT_ID" in msg


def test_secrets_store(tmp_path, monkeypatch):
    monkeypatch.setenv("JOBHUNT_SECRETS_FILE", str(tmp_path / "sec.json"))
    monkeypatch.delenv("JOBHUNT_LLM_API_KEY", raising=False)
    from jobhunt import secrets as S

    assert S.get_secret("JOBHUNT_LLM_API_KEY") == ""
    S.set_secrets({"JOBHUNT_LLM_API_KEY": "sk-abc"})
    assert S.get_secret("JOBHUNT_LLM_API_KEY") == "sk-abc"
    # env wins and locks
    monkeypatch.setenv("JOBHUNT_LLM_API_KEY", "sk-env")
    assert S.get_secret("JOBHUNT_LLM_API_KEY") == "sk-env"
    st = S.status()
    assert st["JOBHUNT_LLM_API_KEY"]["source"] == "env" and st["JOBHUNT_LLM_API_KEY"]["locked"]
    # unknown keys ignored
    S.set_secrets({"EVIL": "x"})
    assert "EVIL" not in S._load()
    # file is 0600
    import stat
    mode = stat.S_IMODE((tmp_path / "sec.json").stat().st_mode)
    assert mode == 0o600


def test_scheduler_fires_and_arms(tmp_path, monkeypatch):
    import time

    from jobhunt import server as srv
    from jobhunt.config import ScheduleConfig, default_config

    class _Stats:
        steps = 1
        matches = 2
        new_matches = [{"score": 80, "title": "X", "company": "Y", "location": "Z"}]

    monkeypatch.setattr("jobhunt.engine.loop.run", lambda cfg, store, max_steps=None: _Stats())
    monkeypatch.setattr("jobhunt.engine.digest.print_digest", lambda *a, **k: None)

    sch = srv.Scheduler(default_config(), str(tmp_path / "s.db"))
    sch.start()
    sch.trigger_now()
    deadline = time.time() + 5
    while time.time() < deadline and sch.last_run_summary() is None:
        time.sleep(0.05)
    sch.stop()
    assert sch.last_run_summary() and sch.last_run_summary()["matches"] == 2

    sch2 = srv.Scheduler(default_config(), str(tmp_path / "s.db"))
    sch2.update(ScheduleConfig(enabled=True, every_hours=2, notify=False))
    assert sch2._next_at > time.time()


def test_local_server_persists_and_guards(tmp_path: Path):
    import json
    import threading
    import time
    import urllib.error
    import urllib.request
    from http.server import HTTPServer

    from jobhunt import server as srv
    from jobhunt.config import default_config

    db = str(tmp_path / "srv.db")
    s = Store(db)
    s.upsert_job(Job(url="https://acme.com/1", title="SB", company="Acme",
                     location="Nice", score=82, source="a"))
    s.close()

    cfg = default_config()
    scheduler = srv.Scheduler(cfg, db)  # not started; just for API surface
    handler = srv._make_handler(cfg, db, "127.0.0.1", 4408,
                                str(tmp_path / "cfg.json"), scheduler)
    httpd = HTTPServer(("127.0.0.1", 4408), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.2)
    base = "http://127.0.0.1:4408"

    def post(path, data, token=None):
        h = {"Content-Type": "application/json"}
        if token:
            h["X-JB-Token"] = token
        req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                     headers=h, method="POST")
        try:
            return urllib.request.urlopen(req).status
        except urllib.error.HTTPError as e:
            return e.code

    try:
        # serving injects the token
        page = urllib.request.urlopen(base + "/").read().decode()
        assert "__JB_TOKEN__" in page
        token = page.split('__JB_TOKEN__="')[1].split('"')[0]
        # guard: no token -> 403
        assert post("/api/move", {"url": "https://acme.com/1", "status": "applied"}) == 403
        # with token -> 200 and persisted
        assert post("/api/move", {"url": "https://acme.com/1", "status": "applied"}, token) == 200
        assert post("/api/move", {"url": "https://acme.com/1", "status": "bogus"}, token) == 400
        s2 = Store(db)
        assert len(s2.get_jobs(status="applied")) == 1
        s2.close()
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_digest_summarises_new_matches():
    from jobhunt.engine.digest import build_digest

    cfg = default_config()
    assert "veille" in build_digest([], cfg)
    text = build_digest(
        [{"score": 82, "title": "Senior Backend", "company": "Acme", "location": "Nice"},
         {"score": 60, "title": "Dev", "company": "Beta", "location": "Lyon"}],
        cfg,
    )
    assert "≥ 75" in text and "Senior Backend" in text


def test_dashboard_renders(tmp_path: Path):
    from jobhunt.dashboard.render import render

    s = Store(str(tmp_path / "t.db"))
    s.upsert_job(Job(url="https://a.com/job/1", title="Senior Backend", company="Acme",
                     location="Nice", score=82, summary="Bon poste", source="a.com",
                     breakdown={"stack": {"score": 32, "max": 40, "matched": ["Node"],
                                          "gaps": [{"item": "K8s", "type": "blocking"}]}}))
    out = render(s, default_config(), tmp_path / "d.html")
    html = out.read_text()
    assert "MyJobAgent" in html and "Senior Backend" in html and "prefers-color-scheme" in html
    s.close()
