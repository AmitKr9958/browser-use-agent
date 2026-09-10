"""Orchestration tests without making an LLM request."""

import inspect
from typing import Any

import pytest

from browser_agent.agents.agent import run_on_tab
from browser_agent.models.india import IndiaRuntimeConfig
from browser_agent.tabs.manager import TabNotFoundError
from browser_agent.tabs.models import TabSelector


class FakeTab:
    def __init__(self, target_id: str = "target-1") -> None:
        self.target_id = target_id
        self.title = "Example"
        self.url = "https://example.com"


class FakeSession:
    def __init__(self, tabs: list[FakeTab] | None = None) -> None:
        self.tabs = tabs if tabs is not None else [FakeTab()]
        self.agent_focus_target_id: str | None = None

    async def get_tabs(self) -> list[FakeTab]:
        return self.tabs

    async def switch_to_tab(self, index: int) -> None:
        self.agent_focus_target_id = self.tabs[index].target_id

    async def get_current_page_url(self) -> str:
        return self.tabs[0].url

    async def get_current_page_title(self) -> str:
        return self.tabs[0].title

    async def stop(self) -> None:
        return None


class FakeHistory:
    def final_result(self) -> str:
        return "ok"


@pytest.mark.asyncio
async def test_run_on_tab_verifies_before_and_after(monkeypatch: Any) -> None:
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

    history = await run_on_tab("Read the page title", TabSelector(target_id="target-1"), browser_session=session)
    assert history.final_result() == "ok"
    assert captured["browser_session"] is session
    assert "Read the page title" in captured["task"]
    assert "locale=en-IN" in captured["task"]
    assert captured["run_kwargs"] == {"max_steps": 100}


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
    assert captured["task"] == "Read"


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
        "Read the page title",
        TabSelector(target_id="target-1"),
        browser_session=session,
        max_steps=2,
        llm_timeout=30,
        step_timeout=45,
    )
    assert captured["llm_timeout"] == 30
    assert captured["step_timeout"] == 45
    assert captured["run_kwargs"] == {"max_steps": 2}


@pytest.mark.asyncio
async def test_run_on_tab_accepts_sync_agent_run(monkeypatch: Any) -> None:
    session = FakeSession()
    verification_session = FakeSession()

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            pass

        def run(self, **kwargs: Any) -> FakeHistory:
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    history = await run_on_tab("Read the page title", TabSelector(target_id="target-1"), browser_session=session)
    assert history.final_result() == "ok"
    assert not inspect.isawaitable(history)


@pytest.mark.asyncio
async def test_run_on_tab_rejects_empty_task() -> None:
    with pytest.raises(ValueError, match="task must not be empty"):
        await run_on_tab("   ", TabSelector(target_id="target-1"), browser_session=FakeSession())


@pytest.mark.asyncio
async def test_run_on_tab_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError, match="max_steps must be at least 1"):
        await run_on_tab("Read", TabSelector(target_id="target-1"), browser_session=FakeSession(), max_steps=0)
    with pytest.raises(ValueError, match="llm_timeout must be at least 1 second"):
        await run_on_tab("Read", TabSelector(target_id="target-1"), browser_session=FakeSession(), llm_timeout=0)
    with pytest.raises(ValueError, match="step_timeout must be at least 1 second"):
        await run_on_tab("Read", TabSelector(target_id="target-1"), browser_session=FakeSession(), step_timeout=0)


@pytest.mark.asyncio
async def test_run_on_tab_fails_if_target_disappears(monkeypatch: Any) -> None:
    session = FakeSession()
    verification_session = FakeSession([FakeTab("different-target")])

    class FakeAgent:
        def __init__(self, **kwargs: Any) -> None:
            pass

        async def run(self, **kwargs: Any) -> FakeHistory:
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    with pytest.raises(TabNotFoundError, match="disappeared"):
        await run_on_tab("Read the page title", TabSelector(target_id="target-1"), browser_session=session)
