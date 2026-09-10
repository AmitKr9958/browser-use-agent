"""LLM provider factory for JobPilot generation tasks."""

from __future__ import annotations

from typing import Any

from browser_use import ChatAnthropic, ChatGoogle, ChatOpenAI


def create_llm(provider: str, model: str) -> Any:
    """Create a Browser Use LLM adapter without coupling JobPilot to one vendor."""
    normalized = provider.strip().lower()
    if not model.strip():
        raise ValueError("model must not be empty")
    if normalized in {"google", "gemini"}:
        return ChatGoogle(model=model)
    if normalized in {"anthropic", "claude"}:
        return ChatAnthropic(model=model)
    if normalized == "openai":
        return ChatOpenAI(model=model)
    raise ValueError(f"Unsupported LLM provider: {provider}. Use google, anthropic, or openai.")
