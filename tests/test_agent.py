"""Tests for the verified Browser Use agent wrapper."""

from __future__ import annotations

from typing import Any

import pytest

from browser_agent.agents.agent import run_on_tab
from browser_agent.models.india import IndiaRuntimeConfig
from browser_agent.tabs.models import TabRecord, TabSelector


class FakeHistory:
    def final_result(self) -> str:
        return "done"


class FakeSession:
    agent_focus_target_id = "target-1"

    async def get_tabs(self) -> list[TabRecord]:
        return [TabRecord(0, "target-1", "Title", "https://example.com")]

    async def get_current_page_url(self) -> str:
        return "https://example.com"

    async def get_current_page_title(self) -> str:
        return "Title"

    async def stop(self) -> None:
        return None


@pytest.mark.asyncio
async def test_run_on_tab_verifies_before_and_after(monkeypatch: Any) -> None:
    session = FakeSession()
    verification_session = FakeSession()
    captured: dict[str, Any] = {}

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def run(self, **kwargs: Any) -> FakeHistory:
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    result = await run_on_tab("Read", TabSelector(target_id="target-1"), browser_session=session)
    assert result.final_result() == "done"
    assert "Task:" in captured["task"]


@pytest.mark.asyncio
async def test_run_on_tab_supports_custom_india_runtime(monkeypatch: Any) -> None:
    session = FakeSession()
    verification_session = FakeSession()
    captured: dict[str, Any] = {}

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def run(self, **kwargs: Any) -> FakeHistory:
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    await run_on_tab(
        "Read",
        TabSelector(target_id="target-1"),
        browser_session=session,
        india_runtime=IndiaRuntimeConfig(locale="hi-IN", timezone="Asia/Kolkata", currency="INR", country_code="IN"),
    )
    assert "locale=hi-IN" in captured["task"]


@pytest.mark.asyncio
async def test_run_on_tab_can_disable_regional_guidance(monkeypatch: Any) -> None:
    session = FakeSession()
    verification_session = FakeSession()
    captured: dict[str, Any] = {}

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def run(self, **kwargs: Any) -> FakeHistory:
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    await run_on_tab("Read", TabSelector(target_id="target-1"), browser_session=session, india_runtime=None)
    assert "locale=" not in captured["task"]
    assert "Sensitive interaction policy" in captured["task"]


@pytest.mark.asyncio
async def test_run_on_tab_passes_execution_limits(monkeypatch: Any) -> None:
    session = FakeSession()
    verification_session = FakeSession()
    captured: dict[str, Any] = {}

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def run(self, **kwargs: Any) -> FakeHistory:
            captured["run_kwargs"] = kwargs
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    await run_on_tab(
        "Read",
        TabSelector(target_id="target-1"),
        browser_session=session,
        max_steps=7,
        llm_timeout=11,
        step_timeout=13,
    )
    assert captured["run_kwargs"] == {"max_steps": 7}
    assert captured["llm_timeout"] == 11
    assert captured["step_timeout"] == 13
