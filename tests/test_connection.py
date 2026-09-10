"""Connection-layer tests; Browser Harness is mocked so CI needs no Chrome."""

from browser_agent.connection import harness


def test_connect_browser_harness_uses_dynamic_ws(monkeypatch):
    class FakeSession:
        def __init__(self, *, cdp_url: str) -> None:
            self.cdp_url: str = cdp_url

    monkeypatch.setattr(harness, "get_ws_url", lambda: "ws://127.0.0.1:64173/devtools/browser/test")
    monkeypatch.setattr(harness, "BrowserSession", FakeSession)

    session = harness.connect_browser_harness()
    assert session.cdp_url.endswith("/devtools/browser/test")


def test_connect_browser_harness_rejects_missing_endpoint(monkeypatch):
    monkeypatch.setattr(harness, "get_ws_url", lambda: None)
    try:
        harness.connect_browser_harness()
    except RuntimeError as exc:
        assert "CDP WebSocket URL" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
