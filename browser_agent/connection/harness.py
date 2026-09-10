"""Connection to the user's existing Browser Harness Chrome instance."""

from __future__ import annotations

from browser_harness.daemon import get_ws_url
from browser_use import BrowserProfile, BrowserSession


def connect_browser_harness() -> BrowserSession:
    """Create a persistent BrowserSession attached to the Harness CDP browser.

    The browser itself is owned by Browser Harness. ``keep_alive=True`` tells
    Browser Use not to kill that external browser when an Agent finishes, which
    is required for repeated local agent runs against the same Chrome session.
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
