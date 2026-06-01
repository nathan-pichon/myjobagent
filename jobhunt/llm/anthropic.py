"""Anthropic provider. Key read locally from cfg.api_key_env."""
from __future__ import annotations

import os

import requests

from jobhunt.config import LLMConfig
from jobhunt.llm.base import LLMError


class AnthropicProvider:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.base_url = (cfg.base_url or "https://api.anthropic.com").rstrip("/")
        if "localhost" in self.base_url:
            self.base_url = "https://api.anthropic.com"
        from jobhunt.secrets import get_secret

        self.api_key = get_secret(cfg.api_key_env)

    def complete(self, prompt: str) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.cfg.model,
                    "max_tokens": 2048,
                    "temperature": self.cfg.temperature,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]
        except (requests.RequestException, KeyError, IndexError) as e:
            raise LLMError(f"Anthropic request failed: {e}") from e

    def health(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, f"No API key in ${self.cfg.api_key_env} (set it locally, never on the web)."
        return True, f"Anthropic configured ({self.cfg.model})"
