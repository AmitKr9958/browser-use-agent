"""Pluggable Browser Use LLM provider construction."""

from __future__ import annotations

from typing import Any

from browser_use import ChatAnthropic, ChatGoogle, ChatOpenAI


def create_llm(provider: str, model: str) -> Any:
    """Create a Browser Use LLM from a provider name.

    The returned object is a native Browser Use LLM, so callers can also pass
    their own provider implementation directly to ``run_on_tab``.
    """
    normalized = provider.strip().casefold()
    if not normalized:
        raise ValueError("provider must not be empty")
    if not model.strip():
        raise ValueError("model must not be empty")

    factories = {
        "google": ChatGoogle,
        "gemini": ChatGoogle,
        "anthropic": ChatAnthropic,
        "claude": ChatAnthropic,
        "openai": ChatOpenAI,
    }
    factory = factories.get(normalized)
    if factory is None:
        supported = ", ".join(sorted({"google", "anthropic", "openai"}))
        raise ValueError(f"Unsupported provider {provider!r}; supported providers: {supported}")
    return factory(model=model)
