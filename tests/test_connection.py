"""Connection-layer tests; Browser Harness is mocked so CI needs no Chrome."""

from typing import cast

from browser_agent.connection import harness


def test_connect_browser_harness_uses_dynamic_ws(monkeypatch):
    class FakeProfile:
        def __init__(self, *, cdp_url: str, is_local: bool, keep_alive: bool) -> None:
            self.cdp_url = cdp_url
            self.is_local = is_local
            self.keep_alive = keep_alive

    class FakeSession:
        def __init__(self, *, browser_profile: FakeProfile) -> None:
            self.browser_profile = browser_profile

    monkeypatch.setattr(harness, "get_ws_url", lambda: "ws://127.0.0.1:64173/devtools/browser/test")
    monkeypatch.setattr(harness, "BrowserProfile", FakeProfile)
    monkeypatch.setattr(harness, "BrowserSession", FakeSession)

    session = cast(FakeSession, harness.connect_browser_harness())
    assert session.browser_profile.cdp_url.endswith("/devtools/browser/test")
    assert session.browser_profile.is_local is True
    assert session.browser_profile.keep_alive is True


def test_connect_browser_harness_rejects_missing_endpoint(monkeypatch):
    monkeypatch.setattr(harness, "get_ws_url", lambda: None)
    try:
        harness.connect_browser_harness()
    except RuntimeError as exc:
        assert "CDP WebSocket URL" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
