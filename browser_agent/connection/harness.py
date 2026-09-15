"""Connection to the user's existing Browser Harness Chrome instance."""

from __future__ import annotations

import inspect
from typing import Any

from browser_harness.daemon import get_ws_url
from browser_use import BrowserProfile, BrowserSession


async def start_browser_harness_session() -> BrowserSession:
    """Create and fully initialize a BrowserSession attached to Harness Chrome."""
    ws_url = get_ws_url()
    if not ws_url:
        raise RuntimeError("Browser Harness did not return a Chrome CDP WebSocket URL")

    profile = BrowserProfile(
        cdp_url=ws_url,
        is_local=True,
        keep_alive=True,
    )
    session = BrowserSession(browser_profile=profile)
    await session.start()
    return session


def connect_browser_harness() -> BrowserSession:
    """Create a BrowserSession attached to the existing Harness CDP browser.

    This synchronous constructor is retained for callers that explicitly manage
    the session lifecycle. Async application workflows should use
    ``start_browser_harness_session`` so CDP is initialized before browser I/O.
    """
    ws_url = get_ws_url()
    if not ws_url:
        raise RuntimeError("Browser Harness did not return a Chrome CDP WebSocket URL")

    profile = BrowserProfile(
        cdp_url=ws_url,
        is_local=True,
        keep_alive=True,
    )
    return BrowserSession(browser_profile=profile)


async def stop_browser_harness_session(session: Any) -> None:
    """Stop a Harness-backed session without assuming a synchronous stop API."""
    stop = getattr(session, "stop", None)
    if callable(stop):
        result = stop()
        if inspect.isawaitable(result):
            await result
