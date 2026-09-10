"""Safe multi-tab control built on Browser Use's public BrowserSession API."""

from __future__ import annotations

from typing import Any

from .models import TabRecord, TabSelector


class TabNotFoundError(LookupError):
    """No tab matched the requested selector."""


class AmbiguousTabError(LookupError):
    """A selector matched more than one tab."""


class TabVerificationError(RuntimeError):
    """The selected browser target is no longer the expected target."""


class TabManager:
    """Enumerate, locate, select, and verify tabs using stable target identity."""

    def __init__(self, browser_session: Any) -> None:
        self.browser_session = browser_session

    async def _ensure_started(self) -> None:
        """Initialize an unattached BrowserSession before reading its target cache."""
        start = getattr(self.browser_session, "start", None)
        if not callable(start):
            return

        # BrowserSession initializes its CDP root during start(). A fresh session
        # otherwise has no cached targets, which makes get_tabs() return [].
        if getattr(self.browser_session, "_cdp_client_root", None) is None:
            await start()

    async def list_tabs(self) -> list[TabRecord]:
        await self._ensure_started()
        tabs = await self.browser_session.get_tabs()
        return [
            TabRecord(
                index=index,
                target_id=str(tab.target_id),
                title=str(tab.title or ""),
                url=str(tab.url or ""),
            )
            for index, tab in enumerate(tabs)
        ]

    async def find_tab(self, selector: TabSelector) -> TabRecord:
        selector.validate()
        tabs = await self.list_tabs()
        matches = [tab for tab in tabs if self._matches(tab, selector)]
        if not matches:
            raise TabNotFoundError(f"No browser tab matched {selector!r}")
        if len(matches) > 1:
            raise AmbiguousTabError(
                f"Selector {selector!r} matched {len(matches)} tabs: "
                + ", ".join(f"#{tab.index} {tab.title!r}" for tab in matches)
            )
        return matches[0]

    async def select_tab(self, selector: TabSelector) -> TabRecord:
        """Switch to exactly one tab and verify stable target identity."""
        selected = await self.find_tab(selector)
        await self.browser_session.switch_to_tab(selected.index)
        await self.verify_tab(selected)
        return selected

    async def verify_tab(self, expected: TabRecord) -> TabRecord:
        """Verify target identity first; metadata is returned as a fresh snapshot."""
        focused_target = getattr(self.browser_session, "agent_focus_target_id", None)
        if focused_target is not None and str(focused_target) != expected.target_id:
            raise TabVerificationError(
                f"Active target changed: expected {expected.target_id}, got {focused_target}"
            )

        actual_url = str(await self.browser_session.get_current_page_url() or "")
        actual_title = str(await self.browser_session.get_current_page_title() or "")
        return TabRecord(expected.index, expected.target_id, actual_title, actual_url)

    @staticmethod
    def _matches(tab: TabRecord, selector: TabSelector) -> bool:
        if selector.index is not None:
            return tab.index == selector.index
        if selector.target_id is not None:
            return tab.target_id == selector.target_id
        if selector.title is not None:
            return tab.title == selector.title
        if selector.url is not None:
            return tab.url == selector.url
        if selector.title_contains is not None:
            return selector.title_contains.casefold() in tab.title.casefold()
        if selector.url_contains is not None:
            return selector.url_contains.casefold() in tab.url.casefold()
        return False
