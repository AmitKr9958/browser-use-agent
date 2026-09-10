"""Connection to the user's existing Browser Harness Chrome instance."""

from __future__ import annotations

from browser_harness.daemon import get_ws_url
from browser_use import BrowserSession


def connect_browser_harness() -> BrowserSession:
    """Create a BrowserSession attached to the dynamically discovered Harness CDP WS."""
    ws_url = get_ws_url()
    if not ws_url:
        raise RuntimeError("Browser Harness did not return a Chrome CDP WebSocket URL")
    return BrowserSession(cdp_url=ws_url)
