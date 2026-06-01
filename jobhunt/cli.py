"""`jobhunt` command-line interface.

Designed as a product surface (DX = UX): clear output, actionable errors.
Commands: init · validate · doctor · run · dashboard.
"""
from __future__ import annotations

import json
import sys
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from jobhunt import __version__
from jobhunt.config import ConfigError, JobHuntConfig, default_config, load_config, load_config_b64

app = typer.Typer(add_completion=False, help="MyJobAgent — local-first job-hunting agent.")
console = Console()

DEFAULT_CONFIG_PATH = "jobhunt.config.json"
DEFAULT_DB_PATH = "jobhunt.db"


def _load(config: str) -> JobHuntConfig:
    try:
        return load_config(config)
    except ConfigError as e:
        console.print(f"[red]✗ Config error[/]\n{e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show the installed version."""
    console.print(f"MyJobAgent (mja) {__version__}")


@app.command()
def init(
    source: str = typer.Argument(None, help="Path to a jobhunt.config.json produced by the web configurator."),
    b64: str = typer.Option(None, "--b64", help="Inline base64url config (the short web path)."),
    out: str = typer.Option(DEFAULT_CONFIG_PATH, "--out", help="Where to write the config."),
    seed: bool = typer.Option(False, "--seed", help="Write the built-in default config (no web needed)."),
    open_dashboard: bool = typer.Option(True, "--open/--no-open", help="Open the local dashboard when done."),
) -> None:
    """Import a configuration locally (file, inline, or built-in seed). Zero server involved."""
    if seed:
        cfg = default_config()
    elif b64:
        try:
            cfg = load_config_b64(b64)
        except ConfigError as e:
            console.print(f"[red]✗[/] {e}")
            raise typer.Exit(1)
    elif source:
        cfg = _load(source)
    else:
        console.print("[red]Nothing to import.[/] Pass a file path, --b64 <code>, or --seed.")
        raise typer.Exit(1)

    Path(out).write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"[green]✓[/] Config written to [bold]{out}[/]")
    console.print("Next: [bold]mja doctor[/] then [bold]mja run[/]")
    if open_dashboard:
        # Confirmation lives locally — the CLI opens the dashboard (the web
        # SPA cannot reliably reach http://localhost over https).
        try:
            _render_and_open(cfg)
        except Exception:  # noqa: BLE001
            pass


@app.command()
def validate(config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c")) -> None:
    """Validate a config file against the schema."""
    cfg = _load(config)
    console.print(f"[green]✓ Config valid[/] (schema {cfg.schema_version})")
    console.print(f"  roles: {', '.join(cfg.profile.roles) or '—'}")
    console.print(f"  stack: {', '.join(cfg.profile.stack_core) or '—'}")
    console.print(f"  LLM: {cfg.llm.provider}/{cfg.llm.model}")


@app.command()
def doctor(config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c")) -> None:
    """Run an environment checklist (Python, config, LLM, scraping, sources)."""
    ok = True
    table = Table(show_header=False, box=None)

    py_ok = sys.version_info >= (3, 11)
    table.add_row("Python ≥ 3.11", _badge(py_ok), f"{sys.version.split()[0]}")
    ok &= py_ok

    cfg = None
    try:
        cfg = load_config(config)
        table.add_row("Config", _badge(True), config)
    except ConfigError as e:
        table.add_row("Config", _badge(False), str(e).splitlines()[0])
        ok = False

    # scraping extra
    try:
        import ddgs  # noqa: F401
        import playwright  # noqa: F401
        table.add_row("Scraping extra", _badge(True), "ddgs + playwright installed")
    except ImportError:
        table.add_row("Scraping extra", _badge(False), "run: pip install 'jobhunt[scrape]' && playwright install chromium")
        ok = False

    if cfg is not None:
        from jobhunt.llm import check_connection

        llm_ok, msg = check_connection(cfg.llm)
        table.add_row(f"LLM ({cfg.llm.provider})", _badge(llm_ok), msg)
        ok &= llm_ok

        # Sources: show which are usable. At least one must be available.
        from jobhunt.sources import get_sources

        any_source = False
        for src in get_sources(cfg):
            s_ok, s_msg = src.available(cfg)
            any_source = any_source or s_ok
            badge = _badge(s_ok) if s_ok else "[yellow]○[/]"
            table.add_row(f"Source · {src.name}", badge, s_msg)
        if not any_source:
            ok = False
        if cfg.sources.linkedin_enabled:
            table.add_row("LinkedIn source", "[yellow]⚠[/]", "enabled — scraping LinkedIn violates their ToS; use at your own risk")

    console.print(Panel(table, title="mja doctor", border_style="green" if ok else "red"))
    raise typer.Exit(0 if ok else 1)


@app.command()
def run(
    config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
    max_steps: int = typer.Option(None, "--max-steps"),
    open_dashboard: bool = typer.Option(True, "--open/--no-open"),
) -> None:
    """Run a hunt: search, filter, score, persist matches locally."""
    cfg = _load(config)
    from jobhunt.engine.loop import run as run_loop
    from jobhunt.store import Store

    store = Store(db)
    console.print(Panel(f"🔦 MyJobAgent — hunting · 🔒 local · {cfg.llm.provider}/{cfg.llm.model}", border_style="blue"))
    try:
        stats = run_loop(cfg, store, max_steps=max_steps)
    except ImportError:
        console.print("[red]✗[/] Scraping not installed. Run: pip install 'jobhunt[scrape]' && playwright install chromium")
        raise typer.Exit(1)
    console.print(
        f"\n[bold]Done[/] · {stats.steps} steps · {stats.urls_seen} URLs · "
        f"[green]{stats.matches} matches[/] ({len(stats.new_matches)} new)"
    )
    from jobhunt.engine.digest import print_digest

    print_digest(stats.new_matches, cfg, notify=False)
    if open_dashboard and stats.matches:
        _render_and_open(cfg, db)
    store.close()


@app.command()
def watch(
    config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
    every: int = typer.Option(360, "--every", help="Minutes between hunts (default 6h)."),
    once: bool = typer.Option(False, "--once", help="Run a single hunt + digest, then exit."),
    notify: bool = typer.Option(True, "--notify/--no-notify", help="Native desktop notification on new matches."),
) -> None:
    """Scheduled hunting + daily digest — the 'ton agent a bossé cette nuit' loop."""
    cfg = _load(config)
    from jobhunt.engine.digest import print_digest
    from jobhunt.engine.loop import run as run_loop
    from jobhunt.store import Store

    def _one() -> None:
        store = Store(db)
        try:
            stats = run_loop(cfg, store)
        except ImportError:
            console.print("[red]✗[/] Scraping not installed: pip install 'jobhunt[scrape]' && playwright install chromium")
            raise typer.Exit(1)
        print_digest(stats.new_matches, cfg, notify=notify)
        store.close()

    if once:
        _one()
        return

    console.print(f"[blue]watch[/] · hunting every {every} min · Ctrl-C to stop · 🔒 local")
    try:
        while True:
            _one()
            console.print(f"[dim]Next hunt in {every} min…[/]")
            time.sleep(every * 60)
    except KeyboardInterrupt:
        console.print("\n[dim]watch stopped.[/]")


@app.command()
def dashboard(
    config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
    port: int = typer.Option(4321, "--port"),
    static: bool = typer.Option(False, "--static", help="Just write an HTML file (no local server)."),
) -> None:
    """Open the local dashboard. By default runs a 127.0.0.1-only server so the
    Kanban drag & drop and 👍/👎 persist directly to your local store."""
    cfg = _load(config)
    if static:
        _render_and_open(cfg, db)
        return
    from jobhunt.server import serve

    console.print(
        f"[blue]Dashboard local[/] → http://127.0.0.1:{port}/  "
        f"· 🔒 127.0.0.1 uniquement, jamais exposé · Ctrl-C pour arrêter"
    )
    if cfg.schedule.enabled:
        console.print(f"[green]⏱[/] Chasse auto toutes les {cfg.schedule.every_hours} h (modifiable dans Réglages).")
    try:
        serve(cfg, db, port=port, config_path=config)
    except OSError as e:
        console.print(f"[red]✗[/] Port {port} indisponible ({e}). Essaie --port ou --static.")
        raise typer.Exit(1)


@app.command()
def feedback(
    url: str = typer.Argument(..., help="Job URL to rate."),
    up: bool = typer.Option(False, "--up", help="👍 relevant"),
    down: bool = typer.Option(False, "--down", help="👎 not relevant"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
) -> None:
    """Rate a match 👍/👎 — the local source of truth on matching quality."""
    if up == down:
        console.print("[red]Pass exactly one of --up / --down.[/]")
        raise typer.Exit(1)
    from jobhunt.store import Store

    store = Store(db)
    store.set_feedback(url, 1 if up else -1)
    store.close()
    console.print(f"[green]✓[/] Feedback saved ({'👍' if up else '👎'}).")


@app.command()
def move(
    url: str = typer.Argument(..., help="Job URL to move in the pipeline."),
    status: str = typer.Argument(..., help="found|interested|applied|interview|offer|rejected"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
) -> None:
    """Move a job along the application pipeline (Kanban)."""
    from jobhunt.store import PIPELINE_STATUSES, Store

    if status not in PIPELINE_STATUSES:
        console.print(f"[red]Invalid status.[/] Use one of: {', '.join(PIPELINE_STATUSES)}")
        raise typer.Exit(1)
    store = Store(db)
    try:
        store.set_status(url, status)
    finally:
        store.close()
    console.print(f"[green]✓[/] Moved to [bold]{status}[/].")


@app.command()
def pipeline(
    config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
) -> None:
    """Show the application pipeline (Kanban) as columns in the terminal."""
    from jobhunt.store import PIPELINE_STATUSES, Store

    store = Store(db)
    cols = {s: store.get_jobs(status=s) for s in PIPELINE_STATUSES}
    store.close()
    table = Table(title="Pipeline de candidatures", show_lines=False)
    for s in PIPELINE_STATUSES:
        table.add_column(f"{s} ({len(cols[s])})", overflow="fold", max_width=24)
    depth = max((len(v) for v in cols.values()), default=0)
    for i in range(depth):
        row = []
        for s in PIPELINE_STATUSES:
            jobs = cols[s]
            row.append(f"{jobs[i]['score']} · {jobs[i]['title'][:20]}" if i < len(jobs) else "")
        table.add_row(*row)
    console.print(table if depth else "[dim]Pipeline vide. Lance `mja run`.[/]")


@app.command()
def tune(
    config: str = typer.Option(DEFAULT_CONFIG_PATH, "--config", "-c"),
    db: str = typer.Option(DEFAULT_DB_PATH, "--db"),
    apply: bool = typer.Option(False, "--apply", help="Write the revised prompt (default: dry-run preview)."),
) -> None:
    """Improve the Recruteur prompt from your 👎 feedback (opt-in, never silent)."""
    cfg = _load(config)
    from jobhunt.engine.supervisor import tune_recruteur
    from jobhunt.store import Store

    store = Store(db)
    tune_recruteur(cfg, store, dry_run=not apply)
    store.close()


def _render_and_open(cfg: JobHuntConfig, db: str = DEFAULT_DB_PATH) -> None:
    from jobhunt.dashboard.render import render
    from jobhunt.store import Store

    store = Store(db)
    out = render(store, cfg, Path("jobhunt_dashboard.html"))
    store.close()
    console.print(f"[green]✓[/] Dashboard → {out}")
    webbrowser.open(out.resolve().as_uri())


def _badge(ok: bool) -> str:
    return "[green]✓[/]" if ok else "[red]✗[/]"


if __name__ == "__main__":
    app()
