"""Tests for the application LLM provider factory."""

import pytest

from browser_agent.llm import create_llm


@pytest.mark.parametrize(
    ("provider", "expected"),
    [("google", "ChatGoogle"), ("gemini", "ChatGoogle"), ("anthropic", "ChatAnthropic"), ("claude", "ChatAnthropic"), ("openai", "ChatOpenAI")],
)
def test_create_llm(provider: str, expected: str) -> None:
    llm = create_llm(provider, "test-model")
    assert type(llm).__name__ == expected


def test_create_llm_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported provider"):
        create_llm("unknown", "test-model")


def test_create_llm_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="provider must not be empty"):
        create_llm("", "test-model")
    with pytest.raises(ValueError, match="model must not be empty"):
        create_llm("google", "")
