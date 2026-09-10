"""Orchestration tests without making an LLM request."""

import pytest

from browser_agent.agents.agent import run_on_tab
from browser_agent.tabs.manager import TabNotFoundError
from browser_agent.tabs.models import TabSelector


class FakeTab:
    def __init__(self, target_id="target-1"):
        self.target_id = target_id
        self.title = "Example"
        self.url = "https://example.com"


class FakeSession:
    def __init__(self, tabs=None):
        self.tabs = tabs if tabs is not None else [FakeTab()]
        self.agent_focus_target_id = None

    async def get_tabs(self):
        return self.tabs

    async def switch_to_tab(self, index):
        self.agent_focus_target_id = self.tabs[index].target_id

    async def get_current_page_url(self):
        return self.tabs[0].url

    async def get_current_page_title(self):
        return self.tabs[0].title

    async def stop(self):
        return None


class FakeHistory:
    def final_result(self):
        return "ok"


@pytest.mark.asyncio
async def test_run_on_tab_verifies_before_and_after(monkeypatch):
    session = FakeSession()
    verification_session = FakeSession()
    captured = {}

    class FakeAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def run(self):
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    history = await run_on_tab("Read the page title", TabSelector(target_id="target-1"), browser_session=session)
    assert history.final_result() == "ok"
    assert captured["browser_session"] is session
    assert captured["task"] == "Read the page title"


@pytest.mark.asyncio
async def test_run_on_tab_rejects_empty_task():
    with pytest.raises(ValueError, match="task must not be empty"):
        await run_on_tab("   ", TabSelector(target_id="target-1"), browser_session=FakeSession())


@pytest.mark.asyncio
async def test_run_on_tab_fails_if_target_disappears(monkeypatch):
    session = FakeSession()
    verification_session = FakeSession([FakeTab("different-target")])

    class FakeAgent:
        def __init__(self, **kwargs):
            pass

        async def run(self):
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)
    monkeypatch.setattr("browser_agent.agents.agent.connect_browser_harness", lambda: verification_session)

    with pytest.raises(TabNotFoundError, match="disappeared"):
        await run_on_tab("Read the page title", TabSelector(target_id="target-1"), browser_session=session)
