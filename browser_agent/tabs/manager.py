"""Safe multi-tab control built on Browser Use's public BrowserSession API."""

from __future__ import annotations

import inspect
from typing import Any, cast

from browser_use.browser.events import SwitchTabEvent

from .models import TabRecord, TabSelector


class TabNotFoundError(LookupError):
    """No tab matched the requested selector."""


class AmbiguousTabError(LookupError):
    """A selector matched more than one tab."""


class TabVerificationError(RuntimeError):
    """The selected browser target is no longer the expected target."""


async def _await_if_needed(value: Any) -> Any:
    """Await a result when it is awaitable; otherwise return it unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value


class TabManager:
    """Enumerate, locate, select, and verify tabs using stable target identity."""

    def __init__(self, browser_session: Any) -> None:
        self.browser_session = browser_session

    async def _ensure_started(self) -> None:
        """Initialize an unattached BrowserSession before reading its target cache."""
        start = getattr(self.browser_session, "start", None)
        if not callable(start):
            return
        if getattr(self.browser_session, "_cdp_client_root", None) is None:
            await _await_if_needed(cast(Any, start)())

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

        # If Chrome is already showing the requested target, do not dispatch a
        # redundant SwitchTabEvent. This avoids re-entering Browser Use's focus
        # watchdog for an already-active external Harness target.
        try:
            current_url = str(await self.browser_session.get_current_page_url() or "")
            current_title = str(await self.browser_session.get_current_page_title() or "")
        except Exception:
            current_url = current_title = ""

        if current_url != selected.url or current_title != selected.title:
            event_bus = getattr(self.browser_session, "event_bus", None)
            dispatch = getattr(event_bus, "dispatch", None)
            if callable(dispatch):
                event = cast(Any, dispatch)(SwitchTabEvent(target_id=selected.target_id))
                await _await_if_needed(event)
                switched_target = await _await_if_needed(
                    cast(Any, event).event_result(raise_if_any=True, raise_if_none=True)
                )
                if str(switched_target) != selected.target_id:
                    raise TabVerificationError(
                        f"Tab switch returned unexpected target: expected {selected.target_id}, got {switched_target}"
                    )
            else:
                switch_to_tab = getattr(self.browser_session, "switch_to_tab", None)
                if not callable(switch_to_tab):
                    raise RuntimeError("BrowserSession has no supported tab-switch mechanism")
                await _await_if_needed(cast(Any, switch_to_tab)(selected.index))

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
        if actual_url != expected.url or actual_title != expected.title:
            raise TabVerificationError(
                f"Active tab metadata changed: expected {expected.title!r} / {expected.url!r}, "
                f"got {actual_title!r} / {actual_url!r}"
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
