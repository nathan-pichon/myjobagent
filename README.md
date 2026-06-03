# 🔦 MyJobAgent

### 👉 [**Configure your agent → nathan-pichon.github.io/myjobagent**](https://nathan-pichon.github.io/myjobagent/)

*[Version française](README.fr.md)*

> **Open-source, local-first** job-hunting agent. Describe your ideal job once;
> your agent searches for it, scores each offer against **your** profile, explains why —
> **and nothing ever leaves your machine.**

MyJobAgent runs **on your machine**, with **your own LLM** (Ollama by default, or an API key).
A 100% static web configurator only generates your config; the hunting and your data stay local.

## Why
- **Explainable matching**: "82/100 — you're only missing Kubernetes" (Stack/Role/Location/Contract rubric breakdown).
- **Privacy by default**: nothing sent out, bring-your-own-LLM.
- **Polished DX**: a clear CLI, a local dashboard, actionable errors.

> **⚠️ Status: alpha.** The engine, CLI and local dashboard work. The web configurator is
> live (link above); the engine isn't on PyPI yet, so you install it from source (below).

## Requirements
- **Python ≥ 3.11**
- **[Ollama](https://ollama.com)** installed and running (for the default local LLM). Or an API key (OpenAI/Anthropic/…).
- **~3 GB of disk**: ~2 GB for the `gemma4:e2b` model, ~150 MB for Chromium (scraping).
- ⏱️ First install takes ~10–15 min (downloads). A hunt runs in the background;
  local LLMs are slow (~tens of seconds per offer), that's normal — let the agent work.

## Installation (from GitHub)
> Not on PyPI yet: install from source. It's 5 commands.

```bash
# 1. Get the project
git clone https://github.com/nathan-pichon/myjobagent.git
cd myjobagent

# 2. Isolated Python environment
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 3. Install MyJobAgent + the scraping engine
pip install -e '.[scrape]'
playwright install chromium          # headless browser, first time only

# 4. Prepare the local LLM (in another terminal, or in the background)
ollama serve &
ollama pull gemma4:e2b               # ~2 GB; light model validated by our quality eval
```

## First run
```bash
mja init --seed     # create a starter config (jobhunt.config.json)
mja doctor          # check everything is ready (Python, LLM, sources…) — aim for green
mja run             # first hunt
mja dashboard       # open the local dashboard (http://127.0.0.1:4321)
```

`mja doctor` is your friend: it lists exactly what's missing and the command to fix it.

> **`mja` lives in the venv.** The command is only available while the project's environment
> is activated. In a **new terminal**, reactivate it first:
> ```bash
> cd myjobagent && source .venv/bin/activate    # Windows: .venv\Scripts\activate
> mja run
> ```
> To type `mja` from anywhere without activating the venv, add a shell alias
> (`~/.zshrc`, `~/.bashrc`): `alias mja="~/myjobagent/.venv/bin/mja"`.

> **Adapt it to your profile**: `mja init --seed` generates a config geared toward *backend
> Node.js / French Riviera* (the original example). Edit `jobhunt.config.json` by hand, or
> regenerate it with the web configurator, then `mja init ~/Downloads/jobhunt.config.json`.

### Which LLM model?
- `gemma4:e2b` (default) — light (~2 GB), fast, good enough. **Ideal to start.**
- `gemma4:e4b` — slightly more precise on ambiguous cases.
- `qwen2.5:7b` or a **cloud API key** (OpenAI/Anthropic…) — maximum quality.

Change the model in `jobhunt.config.json` (`llm.model`) or via ⚙ Settings in the dashboard.
Details and quality numbers: [`eval/RESULTS.md`](eval/RESULTS.md).

### Local dashboard
`mja dashboard` starts a small server **on `127.0.0.1` only** (never exposed to the network):
the Kanban (drag & drop) and your feedback persist directly to your local database. No online
backend. `--static` just writes an HTML file (drag & drop is then remembered in the browser +
an `mja move` command to paste).

**Feedback on a match** — in the offer detail, two toggles feed the agent's strategy
(`mja tune`): **"Not relevant"** (the offer was over-scored) and **"Outdated"** (the offer was
stale/expired). From the CLI: `mja flag <url> irrelevant|outdated [--undo]`.

**Settings (⚙, in the local dashboard)** — everything configurable without the terminal:
- **Keys & credentials** (cloud LLM API key, France Travail credentials) — entered and stored
  **locally** (`0600` file), never sent online. *(The *static* web configurator never asks for a
  key; only the *local* dashboard does, since it runs on your machine.)*
- **Automatic hunting** — enable a recurring hunt every X hours + notification, or
  "▶ Run now". Managed by a local scheduler while the dashboard is running.

Secret resolution: environment variable first, otherwise the local file. A key set via env var
is locked in the UI (shown as such, not editable).

Pipeline tracking from the CLI too: `mja move <url> <status>` · `mja pipeline`.

### Job sources (reliable sourcing)
Sourcing is layered: **official sources first, web search as fallback.**

| Source | Type | Reliability | Offer text |
|---|---|---|---|
| **France Travail** (official API v2) | REST API, OAuth2 | high, legal | **included** → no scraping |
| **Recruitment RSS feeds** | RSS 2.0 / Atom | **high, stable** | **often included** → no scraping |
| Web (DuckDuckGo + scraping) | broad search | variable (rate-limit) | scraped (Playwright), with retry/backoff |
| LinkedIn / Indeed | — | **OFF by default** (anti-scraping ToS) | explicit opt-in |

**RSS feeds** come **pre-filled** with a default list (WeWorkRemotely, Remotive, RemoteOK,
Himalayas…) that you **see and edit** in the local dashboard (⚙ Settings): add/remove feeds in
`Name | url` format, or click "↺ Restore default feeds". If you remove them all, that's
respected (no re-injection). A feed is fetched once per run then filtered locally by keywords;
the Recruteur does the precise scoring afterward.

Offers that arrive **with their text** (France Travail) are scored directly — more reliable
*and* faster (no browser). If one source fails, the run continues with the others.

**Enable France Travail** (recommended): create an app on [francetravail.io](https://francetravail.io),
subscribe to "Offres d'emploi v2", then export the credentials **locally** (never on the web):
```bash
export FRANCE_TRAVAIL_CLIENT_ID=...
export FRANCE_TRAVAIL_CLIENT_SECRET=...
```
`mja doctor` shows the status of each source.

## Architecture
```
jobhunt/
  config.py        # jobhunt.config.json schema (Pydantic) — web ↔ local contract
  llm/             # bring-your-own-LLM (ollama, openai-compat, anthropic)
  sources/         # sourcing layer: france_travail (API) · rss · web_search (fallback)
  engine/          # scout · trieur · recruteur · filters · scrapers · loop
  store/           # local SQLite (jobs, pipeline, feedback, runs)
  dashboard/       # local dashboard rendering + 127.0.0.1 server
  prompts/         # agents' Jinja2 templates
eval/              # matching eval harness (Phase −1, quality GATE)
product/           # product docs (scope, design, roadmap, reviews, decisions)
```

## Status
Alpha (v0.1). Working: engine, CLI, interactive local dashboard, sources (France Travail /
RSS / web), digest, scheduled hunting, feedback. Coming: PyPI release, web configurator
deployment, desktop app. Roadmap: [`product/03_ROADMAP.md`](product/03_ROADMAP.md).

## Contributing
See [`CONTRIBUTING.md`](CONTRIBUTING.md). Guiding principle: **local-first**, no external online
backend, no secrets on the static web side.

## License
AGPL-3.0-or-later. See [`LICENSE`](LICENSE).
