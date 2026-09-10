"""Orchestration tests without making an LLM request."""

import pytest

from browser_agent.agents.agent import run_on_tab
from browser_agent.tabs.models import TabSelector


class FakeTab:
    def __init__(self):
        self.target_id = "target-1"
        self.title = "Example"
        self.url = "https://example.com"


class FakeSession:
    def __init__(self):
        self.tab = FakeTab()
        self.agent_focus_target_id = None

    async def get_tabs(self):
        return [self.tab]

    async def switch_to_tab(self, index):
        assert index == 0
        self.agent_focus_target_id = self.tab.target_id

    async def get_current_page_url(self):
        return self.tab.url

    async def get_current_page_title(self):
        return self.tab.title


class FakeHistory:
    def final_result(self):
        return "ok"


@pytest.mark.asyncio
async def test_run_on_tab_verifies_before_and_after(monkeypatch):
    session = FakeSession()
    captured = {}

    class FakeAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def run(self):
            return FakeHistory()

    monkeypatch.setattr("browser_agent.agents.agent.Agent", FakeAgent)
    monkeypatch.setattr("browser_agent.agents.agent.ChatGoogle", lambda model: model)

    history = await run_on_tab(
        "Read the page title",
        TabSelector(target_id="target-1"),
        browser_session=session,
    )
    assert history.final_result() == "ok"
    assert captured["browser_session"] is session
    assert captured["task"] == "Read the page title"
