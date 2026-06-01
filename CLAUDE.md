# CLAUDE.md

Guidance for Claude Code (and contributors) working in this repository.

## Project Overview

**MyJobAgent** (CLI: `mja`) is an open-source, **local-first** job-hunting agent. It searches
for freelance/CDI tech positions matching a configurable profile, scores each offer against
that profile with an explainable rubric, and presents results in a local dashboard. Everything
runs on the user's machine with their own LLM (Ollama by default, or an API key). The only
thing that leaves the machine is nothing — there is no hosted backend.

The brand is **MyJobAgent**; the Python package is `jobhunt` (kept internal). The CLI command
is `mja` (with `jobhunt` as a backward-compat alias).

## Setup & Run

```bash
python3 -m venv .venv && source .venv/bin/activate   # Python >= 3.11
pip install -e '.[scrape,dev]'
playwright install chromium                           # first time only
ollama serve & ollama pull gemma4:e2b                 # local LLM (default)

mja init --seed     # write a starter jobhunt.config.json
mja doctor          # environment checklist
mja run             # one hunt
mja dashboard       # local dashboard at http://127.0.0.1:4321
pytest -q           # test suite (offline, no LLM needed)
```

## Architecture

The engine is a Python package under `jobhunt/`:

- **`jobhunt/config.py`** — Pydantic schema for `jobhunt.config.json` (the contract shared with
  the static web configurator). Blocks: `profile`, `llm`, `search`, `sources`, `scoring`,
  `filters`, `schedule`. `default_config()` is the seed.
- **`jobhunt/llm/`** — Bring-your-own-LLM provider layer (Protocol): `ollama` (default, HTTP
  direct), `openai_compat` (OpenAI/LM Studio/Mistral/Groq), `anthropic`. API keys are read
  **locally** (env or `jobhunt/secrets.py`), never embedded in config, never entered on the web.
- **`jobhunt/sources/`** — Pluggable job sources, official-first then web fallback:
  `france_travail` (API v2, returns offer text → no scraping), `rss` (RSS 2.0/Atom, stdlib),
  `web_search` (DuckDuckGo via `ddgs`, with retry/backoff). Add a source by implementing the
  `Source` protocol in `base.py` and registering it in `get_sources()`.
- **`jobhunt/engine/`** — The hunt loop and agents:
  - **Scout** (`prompts/scout.md`) — generates the next search query, or STOP.
  - **Trieur** (`prompts/trieur.md`) — classifies a URL as a single job page vs. noise; code
    fast-track/reject patterns bypass the LLM for obvious cases (`filters.py`).
  - **Recruteur** (`prompts/recruteur.md`) — scores an offer 0–100 against the profile with a
    **typed, explainable breakdown** (Stack 40 / Role 20 / Location 25 / Contract 15 + gaps).
    HARD GATES (stack/location/not-a-job) keep precision high — see `eval/RESULTS.md`.
  - **loop.py** — orchestration: offers that already carry text (France Travail, RSS) are scored
    directly; URL-only offers are queued for scraping (`scrapers.py`, Playwright + stealth).
  - **digest.py** — daily digest of new matches (+ OS notification). **supervisor.py** — opt-in
    prompt tuning from 👎 feedback (`mja tune`).
- **`jobhunt/store/`** — Local SQLite (`jobhunt.db`): jobs (+ breakdown, pipeline status,
  👍/👎 feedback), runs, visited URLs, searches, rejected ("why-not"). `migrate.py` imports the
  legacy `memory.json`.
- **`jobhunt/server.py`** — Local dashboard server, **127.0.0.1 only** (never exposed). Serves
  the dashboard and a tiny token-guarded API (`/api/move`, `/api/feedback`, `/api/secrets`,
  `/api/schedule`, `/api/rss`) that writes directly to SQLite. Includes the recurring-hunt
  `Scheduler` thread.
- **`jobhunt/dashboard/render.py`** — Self-contained HTML dashboard (light/dark, AA colors):
  JobCards with explainable ScoreBreakdown, Kanban pipeline (drag & drop + modal detail),
  why-not section, ⚙ Settings panel (keys, schedule, RSS feeds).
- **`jobhunt/cli.py`** — Typer CLI: `init`, `validate`, `doctor`, `run`, `watch`, `dashboard`,
  `move`, `pipeline`, `feedback`, `tune`, `version`.

Other top-level dirs:
- **`web/`** — Static configurator (Astro + Tailwind), deployable to GitHub Pages/Vercel with
  **zero backend**. Generates a `jobhunt.config.json`. Never asks for API keys.
- **`eval/`** — Matching-quality harness (the GATE). `python -m eval.run` measures
  precision/recall on a labelled dataset. Keep precision ≥ 0.70 after any Recruteur prompt change.
- **`product/`** — Product docs (scope, design, roadmap, reviews, decisions).

## Conventions

- **Local-first, no external backend.** The web stays 100% static. A local 127.0.0.1 server is OK.
- **No secrets in code or in the shared config.** Keys are local-only (`jobhunt/secrets.py`,
  env vars, or the dashboard ⚙ panel). The static web never collects keys.
- **Language:** agent prompts and console logs in **English** (the small local model is
  English-centric); the Recruteur's `summary` field is in **French** (user-facing). Keep this.
- **Tests:** add a test in `tests/test_core.py` for new behavior; keep the suite green.
- Default LLM is `gemma4:e2b` (light, passes the GATE). See `README.md` for alternatives.
