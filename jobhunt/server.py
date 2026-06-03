"""Local dashboard server — 127.0.0.1 only, stdlib only, zero external host.

Serves the dashboard and a tiny JSON API that writes directly to the local
SQLite store, so the Kanban drag & drop and "not relevant" feedback persist for real
without copy-pasting commands.

Security model (it's a personal local tool, but we still guard against
drive-by requests from other web pages the user may have open):
  * Bind to 127.0.0.1 only — never reachable from the network.
  * A random per-session token is embedded in the page and required on every
    API call (other origins can't read it, so they can't forge calls).
  * Reject requests whose Origin isn't our own.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from jobhunt.config import JobHuntConfig
from jobhunt.store import PIPELINE_STATUSES, Store

TOKEN = secrets.token_urlsafe(16)


def _make_handler(cfg: JobHuntConfig, db: str, host: str, port: int, config_path: str, scheduler):
    from jobhunt.dashboard.render import render

    origin_ok = {f"http://{host}:{port}", f"http://localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        # silence default logging noise
        def log_message(self, *a):  # noqa: D401
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj: dict) -> None:
            self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

        def _guard(self) -> bool:
            if self.headers.get("X-JB-Token") != TOKEN:
                self._json(403, {"error": "bad token"})
                return False
            origin = self.headers.get("Origin")
            if origin and origin not in origin_ok:
                self._json(403, {"error": "bad origin"})
                return False
            return True

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                out = Path(".jobhunt_dashboard.html")
                store = Store(db)
                render(store, cfg, out)
                store.close()
                doc = out.read_text(encoding="utf-8")
                # inject the API token so the page can talk to us
                doc = doc.replace("</head>", f'<script>window.__JB_TOKEN__="{TOKEN}"</script></head>', 1)
                self._send(200, doc.encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/api/health":
                self._json(200, {"ok": True})
            elif self.path == "/api/state":
                # Lightweight live state for the auto-refreshing dashboard: hunt
                # status/progress + a cheap signature of the jobs table so the
                # page knows WHEN new cards appeared (without refetching them).
                store = Store(db)
                row = store.conn.execute(
                    "SELECT COUNT(*) n, COALESCE(MAX(first_seen),0) last FROM jobs"
                ).fetchone()
                total = store.conn.execute(
                    "SELECT COUNT(*) n FROM jobs WHERE score >= ?", (cfg.scoring.threshold,)
                ).fetchone()["n"]
                store.close()
                self._json(200, {
                    "running": scheduler.is_running(),
                    "progress": scheduler.progress(),
                    "last_run": scheduler.last_run_summary(),
                    "jobs_count": row["n"],
                    "matches_count": total,
                    "last_added": row["last"],
                })
            elif self.path == "/api/settings":
                from jobhunt.secrets import status as secret_status

                self._json(200, {
                    "secrets": secret_status(),
                    "schedule": cfg.schedule.model_dump(),
                    "llm": {"provider": cfg.llm.provider, "model": cfg.llm.model},
                    "rss": {
                        "enabled": cfg.sources.rss_enabled,
                        "feeds": [f.model_dump() for f in cfg.sources.rss_feeds],
                        "defaults": _rss_defaults(),
                    },
                    "running": scheduler.is_running(),
                    "last_run": scheduler.last_run_summary(),
                })
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:
            if not self._guard():
                return
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._json(400, {"error": "bad json"})
                return

            if self.path == "/api/move":
                url, status = payload.get("url"), payload.get("status")
                if status not in PIPELINE_STATUSES or not url:
                    self._json(400, {"error": "bad params"})
                    return
                store = Store(db)
                store.set_status(url, status)
                store.close()
                self._json(200, {"ok": True})
            elif self.path == "/api/feedback-kind":
                # {url, kind: "irrelevant"|"outdated"|null} — the feedback the
                # Supervisor uses to refine strategy. null/'' clears it.
                from jobhunt.store import FEEDBACK_KINDS

                url, kind = payload.get("url"), payload.get("kind")
                if not url or (kind and kind not in FEEDBACK_KINDS):
                    self._json(400, {"error": "bad params"})
                    return
                store = Store(db)
                store.set_feedback_kind(url, kind)
                store.close()
                self._json(200, {"ok": True})
            elif self.path == "/api/secrets":
                # {updates: {NAME: value, ...}} — empty value deletes. Stored
                # locally only (0600 file), never sent anywhere.
                from jobhunt.secrets import KNOWN, set_secrets, status as secret_status

                updates = payload.get("updates", {})
                if not isinstance(updates, dict) or any(k not in KNOWN for k in updates):
                    self._json(400, {"error": "unknown secret key"})
                    return
                set_secrets({k: str(v) for k, v in updates.items()})
                self._json(200, {"ok": True, "secrets": secret_status()})
            elif self.path == "/api/schedule":
                # {enabled: bool, every_hours: float, notify: bool}
                from jobhunt.config import ScheduleConfig

                try:
                    sched = ScheduleConfig.model_validate({
                        "enabled": bool(payload.get("enabled", False)),
                        "every_hours": float(payload.get("every_hours", 6.0)),
                        "notify": bool(payload.get("notify", True)),
                    })
                except Exception as e:  # noqa: BLE001
                    self._json(400, {"error": f"bad schedule: {e}"})
                    return
                cfg.schedule = sched
                _save_config(cfg, config_path)
                scheduler.update(sched)
                self._json(200, {"ok": True, "schedule": sched.model_dump(),
                                 "running": scheduler.is_running()})
            elif self.path == "/api/run-now":
                scheduler.trigger_now()
                self._json(200, {"ok": True})
            elif self.path == "/api/rss":
                # {enabled: bool, feeds: [{name, url, enabled}]}
                from jobhunt.config import RssFeed

                try:
                    feeds = [
                        RssFeed.model_validate(f)
                        for f in payload.get("feeds", [])
                        if f.get("url")
                    ]
                except Exception as e:  # noqa: BLE001
                    self._json(400, {"error": f"bad feed: {e}"})
                    return
                cfg.sources.rss_enabled = bool(payload.get("enabled", True))
                cfg.sources.rss_feeds = feeds
                _save_config(cfg, config_path)
                self._json(200, {"ok": True, "rss": {
                    "enabled": cfg.sources.rss_enabled,
                    "feeds": [f.model_dump() for f in feeds],
                }})
            else:
                self._json(404, {"error": "not found"})

    return Handler


def _rss_defaults() -> list[dict]:
    from jobhunt.sources.rss import default_feeds

    return default_feeds()


def _save_config(cfg: JobHuntConfig, config_path: str) -> None:
    try:
        Path(config_path).write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
    except OSError:
        pass


class Scheduler:
    """Runs hunts on a timer in a background thread. Configurable live from the
    dashboard. All local — no external trigger."""

    def __init__(self, cfg: JobHuntConfig, db: str):
        self.cfg = cfg
        self.db = db
        self._sched = cfg.schedule
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._running = False           # a hunt is in progress right now
        self._last: dict | None = None
        self._progress: dict | None = None  # live progress during a hunt
        self._next_at: float = 0.0
        self._thread: threading.Thread | None = None

    # --- public API used by the HTTP handler ----------------------------- #
    def is_running(self) -> bool:
        return self._running

    def last_run_summary(self) -> dict | None:
        return self._last

    def progress(self) -> dict | None:
        return self._progress

    def update(self, sched) -> None:
        self._sched = sched
        self.cfg.schedule = sched
        self._reschedule()
        self._wake.set()

    def trigger_now(self) -> None:
        self._next_at = time.time()  # due now (must be > 0 to be truthy)
        self._wake.set()

    # --- internals -------------------------------------------------------- #
    def _reschedule(self) -> None:
        if self._sched.enabled:
            self._next_at = time.time() + self._sched.every_hours * 3600
        else:
            self._next_at = 0.0

    def _run_once(self) -> None:
        from jobhunt.engine.digest import print_digest
        from jobhunt.engine.loop import run as run_loop

        self._running = True

        def _on_progress(stats) -> None:
            self._progress = {
                "phase": stats.phase, "steps": stats.steps,
                "urls_seen": stats.urls_seen, "matches": stats.matches,
                "new": len(stats.new_matches), "last_match": stats.last_match,
            }

        try:
            store = Store(self.db)
            stats = run_loop(self.cfg, store, on_progress=_on_progress)
            store.close()
            print_digest(stats.new_matches, self.cfg, notify=self._sched.notify)
            self._last = {
                "at": time.time(), "matches": stats.matches,
                "new": len(stats.new_matches), "steps": stats.steps,
            }
        except Exception as e:  # noqa: BLE001
            self._last = {"at": time.time(), "error": str(e)}
        finally:
            self._running = False
            self._progress = None

    def _loop(self) -> None:
        self._reschedule()
        while not self._stop.is_set():
            now = time.time()
            if self._next_at and now >= self._next_at and not self._running:
                self._run_once()
                if self._sched.enabled:
                    self._next_at = time.time() + self._sched.every_hours * 3600
                else:
                    self._next_at = 0.0
            # wait up to 5s or until woken by a config change / manual trigger
            self._wake.wait(timeout=5)
            self._wake.clear()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()


def serve(cfg: JobHuntConfig, db: str = "jobhunt.db", *, host: str = "127.0.0.1",
          port: int = 4321, open_browser: bool = True, config_path: str = "jobhunt.config.json") -> None:
    scheduler = Scheduler(cfg, db)
    scheduler.start()
    handler = _make_handler(cfg, db, host, port, config_path, scheduler)
    httpd = HTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()
        httpd.server_close()
