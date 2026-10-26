"""LLM port — the one place a model is called. MVP default is a deterministic stub so the whole
pipeline runs offline. Set a provider key (e.g. OPENAI_API_KEY) and install litellm to switch the
reasoning steps onto a real model behind the same interface.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
import os


class LLMPort(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str: ...

    def explain_product(self, name: str, sql: str, cols: list[str]) -> str:
        """Human-readable description of a generated product. Overridable; has a safe default."""
        return (f"'{name}' aggregates the cataloged invoices into {', '.join(cols)}. "
                f"Generated and validated automatically from your prompt.")


class StubLLM(LLMPort):
    """No network. Returns template text; structural logic lives in the agents, not here."""
    def complete(self, prompt: str) -> str:
        return "[stub-llm] (no model configured — deterministic fallback in use)"


class LiteLLM(LLMPort):
    def __init__(self, model: str):
        import litellm  # noqa: F401
        self._litellm = litellm
        self.model = model

    def complete(self, prompt: str) -> str:
        resp = self._litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp["choices"][0]["message"]["content"]

    def explain_product(self, name: str, sql: str, cols: list[str]) -> str:
        return self.complete(
            "In two plain sentences for a business user, describe the data product this SQL "
            f"produces (columns: {cols}). Do not restate the SQL.\n\n{sql}"
        )


def get_llm(cfg: dict) -> LLMPort:
    provider = cfg.get("provider", "auto")
    has_key = any(os.environ.get(k) for k in
                  ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AZURE_API_KEY", "VERTEX_PROJECT"))
    if provider == "stub" or (provider == "auto" and not has_key):
        return StubLLM()
    try:
        return LiteLLM(cfg.get("model", "gpt-4o-mini"))
    except Exception:
        # litellm not installed or misconfigured — stay offline rather than crash the demo.
        return StubLLM()
