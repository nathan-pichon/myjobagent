"""Local secrets store — API keys & credentials, on the machine only.

Secrets live in a separate local file (NOT in jobhunt.config.json, which is the
shareable config the static web generates). Resolution order for any secret:
  1. environment variable (wins — good for CI / power users)
  2. the local secrets file (~/.jobhunt or ./.jobhunt_secrets.json)

Written with 0600 permissions. Never committed (see .gitignore). This is what
lets the local dashboard UI manage keys without ever sending them anywhere.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

SECRETS_FILE = ".jobhunt_secrets.json"

# Known secret keys (name shown in the UI, env var that overrides it).
KNOWN = {
    "JOBHUNT_LLM_API_KEY": "Clé API du LLM (OpenAI / Anthropic / Mistral / Groq)",
    "FRANCE_TRAVAIL_CLIENT_ID": "France Travail — Client ID",
    "FRANCE_TRAVAIL_CLIENT_SECRET": "France Travail — Client Secret",
}


def _path() -> Path:
    return Path(os.environ.get("JOBHUNT_SECRETS_FILE", SECRETS_FILE))


def _load() -> dict[str, str]:
    p = _path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_secret(name: str) -> str:
    """Env var first, then the local secrets file."""
    val = os.environ.get(name)
    if val:
        return val
    return _load().get(name, "")


def set_secrets(updates: dict[str, str]) -> None:
    """Merge updates into the local secrets file (0600). Empty string deletes."""
    data = _load()
    for k, v in updates.items():
        if k not in KNOWN:
            continue
        if v:
            data[k] = v
        else:
            data.pop(k, None)
    p = _path()
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        p.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass


def status() -> dict[str, dict]:
    """For the UI: which secrets are set and from where (without revealing them)."""
    data = _load()
    out = {}
    for name, label in KNOWN.items():
        from_env = bool(os.environ.get(name))
        from_file = name in data
        out[name] = {
            "label": label,
            "set": from_env or from_file,
            "source": "env" if from_env else ("file" if from_file else None),
            "locked": from_env,  # env wins; UI can't override it
        }
    return out
