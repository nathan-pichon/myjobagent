"""LLM provider abstraction — bring-your-own-LLM.

Default is Ollama (local). Cloud providers read their key locally (keychain or
JOBHUNT_LLM_API_KEY); keys are never embedded in the shared config nor entered
on the web.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from jobhunt.config import LLMConfig


class LLMError(Exception):
    pass


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, prompt: str) -> str:
        """Return the model's text completion for a single prompt."""
        ...

    def health(self) -> tuple[bool, str]:
        """Return (ok, message) describing connectivity."""
        ...


def get_provider(cfg: LLMConfig) -> LLMProvider:
    if cfg.provider == "ollama":
        from jobhunt.llm.ollama import OllamaProvider

        return OllamaProvider(cfg)
    if cfg.provider in ("openai", "lmstudio", "mistral", "groq"):
        from jobhunt.llm.openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(cfg)
    if cfg.provider == "anthropic":
        from jobhunt.llm.anthropic import AnthropicProvider

        return AnthropicProvider(cfg)
    raise LLMError(f"Unknown LLM provider: {cfg.provider}")


def check_connection(cfg: LLMConfig) -> tuple[bool, str]:
    try:
        return get_provider(cfg).health()
    except Exception as e:  # noqa: BLE001
        return False, str(e)
