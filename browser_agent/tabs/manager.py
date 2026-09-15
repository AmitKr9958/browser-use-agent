"""Safe multi-tab control built on Browser Use's public BrowserSession API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from browser_use.browser.events import SwitchTabEvent

from browser_agent.connection.session_manager import BrowserSessionManager
from browser_agent.utils import await_if_needed
from .models import TabRecord, TabSelector

logger = logging.getLogger(__name__)


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
        async with BrowserSessionManager(self.browser_session):
            return

    async def list_tabs(self, timeout: float = 10.0) -> list[TabRecord]:
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        await self._ensure_started()
        try:
            tabs = await asyncio.wait_for(self.browser_session.get_tabs(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            logger.error("get_tabs timed out after %.2fs", timeout)
            raise TimeoutError(f"Failed to list browser tabs within {timeout} seconds") from exc
        except Exception as exc:
            logger.error("Failed to list browser tabs: %s", exc, exc_info=True)
            raise RuntimeError("Failed to list browser tabs") from exc
        return [
            TabRecord(
                index=index,
                target_id=str(tab.target_id),
                title=str(tab.title or ""),
                url=str(tab.url or ""),
            )
            for index, tab in enumerate(tabs)
        ]

    async def find_tab(self, selector: TabSelector, timeout: float = 10.0) -> TabRecord:
        selector.validate()
        tabs = await self.list_tabs(timeout=timeout)
        matches = [tab for tab in tabs if self._matches(tab, selector)]
        if not matches:
            raise TabNotFoundError(f"No browser tab matched {selector!r}")
        if len(matches) > 1:
            raise AmbiguousTabError(
                f"Selector {selector!r} matched {len(matches)} tabs: "
                + ", ".join(f"#{tab.index} {tab.title!r}" for tab in matches)
            )
        return matches[0]

    async def select_tab(self, selector: TabSelector, timeout: float = 10.0) -> TabRecord:
        """Switch to exactly one tab and verify stable target identity."""
        selected = await self.find_tab(selector, timeout=timeout)
        try:
            current_url = str(
                await asyncio.wait_for(self.browser_session.get_current_page_url(), timeout=timeout)
                or ""
            )
            current_title = str(
                await asyncio.wait_for(self.browser_session.get_current_page_title(), timeout=timeout)
                or ""
            )
        except asyncio.TimeoutError as exc:
            logger.warning("Timeout reading current page metadata for tab %s", selected.target_id)
            raise TimeoutError("Cannot verify current tab state within the configured timeout") from exc
        except Exception as exc:
            logger.error(
                "Failed to read current page metadata for tab %s: %s",
                selected.target_id,
                exc,
                exc_info=True,
            )
            raise RuntimeError("Cannot verify current tab state before switching") from exc

        if current_url != selected.url or current_title != selected.title:
            event_bus = getattr(self.browser_session, "event_bus", None)
            dispatch = getattr(event_bus, "dispatch", None)
            if callable(dispatch):
                event = dispatch(SwitchTabEvent(target_id=selected.target_id))
                await await_if_needed(event)
                switched_target = await await_if_needed(
                    event.event_result(raise_if_any=True, raise_if_none=True)
                )
                if str(switched_target) != selected.target_id:
                    raise TabVerificationError(
                        f"Tab switch returned unexpected target: expected {selected.target_id}, got {switched_target}"
                    )
            else:
                switch_to_tab = getattr(self.browser_session, "switch_to_tab", None)
                if not callable(switch_to_tab):
                    raise RuntimeError("BrowserSession has no supported tab-switch mechanism")
                await await_if_needed(switch_to_tab(selected.index))

        return await self.verify_tab(selected, timeout=timeout)

    async def verify_tab(self, expected: TabRecord, timeout: float = 10.0) -> TabRecord:
        """Verify target identity and current metadata on the same session."""
        if timeout <= 0:
            raise ValueError("timeout must be greater than 0")

        # Browser Use exposes the active target through agent_focus_target_id. Some
        # lightweight/test sessions don't expose that field, so fall back to the
        # session's current target id and finally verify that the expected target
        # still exists in the live target list. This prevents stale URL/title data
        # from making a changed/closed target look successfully verified.
        active_target: str | None = None
        focused_target = getattr(self.browser_session, "agent_focus_target_id", None)
        if focused_target is not None:
            active_target = str(focused_target)
        else:
            session_target = getattr(self.browser_session, "_target_id", None)
            if session_target is not None:
                active_target = str(session_target)

        try:
            if active_target is None:
                get_target_info = getattr(self.browser_session, "get_current_target_info", None)
                if callable(get_target_info):
                    target_info = await asyncio.wait_for(
                        await_if_needed(get_target_info()), timeout=timeout
                    )
                    target_id = getattr(target_info, "target_id", None) if target_info is not None else None
                    if target_id is not None:
                        active_target = str(target_id)

            actual_url = str(
                await asyncio.wait_for(self.browser_session.get_current_page_url(), timeout=timeout)
                or ""
            )
            actual_title = str(
                await asyncio.wait_for(self.browser_session.get_current_page_title(), timeout=timeout)
                or ""
            )

            if active_target is None:
                tabs = await asyncio.wait_for(self.browser_session.get_tabs(), timeout=timeout)
                target_ids = {str(tab.target_id) for tab in tabs}
                if expected.target_id not in target_ids:
                    raise TabVerificationError(
                        f"Active target changed: expected {expected.target_id}, but that target is no longer active"
                    )
            elif active_target != expected.target_id:
                raise TabVerificationError(
                    f"Active target changed: expected {expected.target_id}, got {active_target}"
                )
        except TabVerificationError:
            raise
        except asyncio.TimeoutError as exc:
            raise TimeoutError("Failed to verify active browser tab within the configured timeout") from exc
        except Exception as exc:
            logger.error("Failed to verify tab %s: %s", expected.target_id, exc, exc_info=True)
            raise RuntimeError("Failed to verify active browser tab") from exc

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
