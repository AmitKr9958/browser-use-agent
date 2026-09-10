"""Tests for safe AI fallback application answers."""

import pytest

from jobpilot import Job, ResumeProfile, answer_application_question


class _Response:
    content = "Supported answer"


class _LLM:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, messages: object) -> _Response:
        self.calls += 1
        return _Response()


@pytest.mark.asyncio
async def test_sensitive_question_needs_review_without_llm_call() -> None:
    llm = _LLM()
    result = await answer_application_question(
        llm,
        Job(title="Engineer", company="Example", url="https://example.com/job"),
        ResumeProfile(name="Amit", email="amit@example.com"),
        "What is your Aadhaar Number?",
    )
    assert result == "NEEDS_REVIEW"
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_safe_question_uses_llm() -> None:
    llm = _LLM()
    result = await answer_application_question(
        llm,
        Job(title="Engineer", company="Example", url="https://example.com/job"),
        ResumeProfile(name="Amit", email="amit@example.com"),
        "Why are you interested in this role?",
    )
    assert result == "Supported answer"
    assert llm.calls == 1
