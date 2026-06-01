"""OpenAI-compatible provider (OpenAI, LM Studio, Mistral, Groq).

The API key is read LOCALLY from the env var named by `cfg.api_key_env`
(default JOBHUNT_LLM_API_KEY). It is never part of the shared config nor
entered on the web. LM Studio runs locally and usually needs no key.
"""
from __future__ import annotations

import os

import requests

from jobhunt.config import LLMConfig
from jobhunt.llm.base import LLMError

_DEFAULT_BASE = {
    "openai": "https://api.openai.com/v1",
    "mistral": "https://api.mistral.ai/v1",
    "groq": "https://api.groq.com/openai/v1",
    "lmstudio": "http://localhost:1234/v1",
}


class OpenAICompatProvider:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.base_url = (cfg.base_url or _DEFAULT_BASE.get(cfg.provider, "")).rstrip("/")
        if not self.base_url or self.base_url == "http://localhost:11434":
            self.base_url = _DEFAULT_BASE.get(cfg.provider, "")
        from jobhunt.secrets import get_secret

        self.api_key = get_secret(cfg.api_key_env)

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def complete(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json={
                    "model": self.cfg.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": self.cfg.temperature,
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except (requests.RequestException, KeyError, IndexError) as e:
            raise LLMError(f"{self.cfg.provider} request failed: {e}") from e

    def health(self) -> tuple[bool, str]:
        if self.cfg.provider != "lmstudio" and not self.api_key:
            return False, (
                f"No API key found in ${self.cfg.api_key_env}. "
                f"Set it locally (keychain/env) — never on the web."
            )
        try:
            resp = requests.get(f"{self.base_url}/models", headers=self._headers(), timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            return False, f"{self.cfg.provider} unreachable at {self.base_url} ({e})"
        return True, f"{self.cfg.provider} OK ({self.cfg.model})"
