"""Safe multi-tab control built on Browser Use's public BrowserSession API."""

from __future__ import annotations

from typing import Any

from .models import TabRecord, TabSelector


class TabNotFoundError(LookupError):
    """No tab matched the requested selector."""


class AmbiguousTabError(LookupError):
    """A selector matched more than one tab."""


class TabVerificationError(RuntimeError):
    """The selected tab did not match its post-switch verification criteria."""


class TabManager:
    """Enumerate, locate, select, and verify tabs without relying on visible order alone."""

    def __init__(self, browser_session: Any) -> None:
        self.browser_session = browser_session

    async def list_tabs(self) -> list[TabRecord]:
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
        """Switch to exactly one tab and verify URL/title after switching."""
        selected = await self.find_tab(selector)
        await self.browser_session.switch_to_tab(selected.index)
        await self.verify_tab(selected)
        return selected

    async def verify_tab(self, expected: TabRecord) -> TabRecord:
        """Re-read the active page and fail closed if it is not the expected tab."""
        actual_url = str(await self.browser_session.get_current_page_url() or "")
        actual_title = str(await self.browser_session.get_current_page_title() or "")
        if actual_url != expected.url or actual_title != expected.title:
            raise TabVerificationError(
                "Active tab verification failed: "
                f"expected title={expected.title!r}, url={expected.url!r}; "
                f"got title={actual_title!r}, url={actual_url!r}"
            )
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
