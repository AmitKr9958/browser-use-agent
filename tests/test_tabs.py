"""Unit tests for deterministic tab selection; no browser or API key required."""

import pytest

from browser_agent.tabs.manager import AmbiguousTabError, TabManager, TabNotFoundError
from browser_agent.tabs.models import TabSelector


class FakeTab:
    def __init__(self, target_id: str, title: str, url: str) -> None:
        self.target_id = target_id
        self.title = title
        self.url = url


class FakeSession:
    def __init__(self) -> None:
        self.tabs = [
            FakeTab("target-google", "Google", "https://www.google.com/"),
            FakeTab("target-github", "GitHub", "https://github.com/"),
            FakeTab("target-router", "9Router", "https://9router.com/"),
        ]
        self.agent_focus_target_id = None
        self.active = 0

    async def get_tabs(self):
        return self.tabs

    async def switch_to_tab(self, index: int):
        self.active = index
        self.agent_focus_target_id = self.tabs[index].target_id

    async def get_current_page_url(self):
        return self.tabs[self.active].url

    async def get_current_page_title(self):
        return self.tabs[self.active].title


class StartableFakeSession(FakeSession):
    def __init__(self) -> None:
        super().__init__()
        self._cdp_client_root = None
        self.started = False

    async def start(self):
        self.started = True
        self._cdp_client_root = object()


@pytest.mark.asyncio
async def test_list_tabs_returns_stable_records():
    manager = TabManager(FakeSession())
    tabs = await manager.list_tabs()
    assert [(t.index, t.target_id, t.title, t.url) for t in tabs] == [
        (0, "target-google", "Google", "https://www.google.com/"),
        (1, "target-github", "GitHub", "https://github.com/"),
        (2, "target-router", "9Router", "https://9router.com/"),
    ]


@pytest.mark.asyncio
async def test_list_tabs_starts_uninitialized_session():
    session = StartableFakeSession()
    manager = TabManager(session)
    tabs = await manager.list_tabs()
    assert session.started is True
    assert len(tabs) == 3


@pytest.mark.asyncio
async def test_select_tab_by_target_id_verifies_focus():
    session = FakeSession()
    manager = TabManager(session)
    selected = await manager.select_tab(TabSelector(target_id="target-router"))
    assert selected.target_id == "target-router"
    assert session.active == 2


@pytest.mark.asyncio
async def test_contains_selector_is_case_insensitive():
    manager = TabManager(FakeSession())
    selected = await manager.find_tab(TabSelector(title_contains="GITHUB"))
    assert selected.target_id == "target-github"


@pytest.mark.asyncio
async def test_missing_tab_fails_closed():
    manager = TabManager(FakeSession())
    with pytest.raises(TabNotFoundError):
        await manager.find_tab(TabSelector(url_contains="does-not-exist"))


@pytest.mark.asyncio
async def test_ambiguous_selector_fails_closed():
    session = FakeSession()
    session.tabs.append(FakeTab("target-github-2", "GitHub", "https://github.com/second"))
    manager = TabManager(session)
    with pytest.raises(AmbiguousTabError):
        await manager.find_tab(TabSelector(title="GitHub"))


def test_selector_requires_exactly_one_field():
    with pytest.raises(ValueError):
        TabSelector(title="GitHub", url="https://github.com/").validate()
