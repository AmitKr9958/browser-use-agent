"""Deterministic one-off browser actions for the command-line interface."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, cast

from browser_agent.connection.harness import connect_browser_harness


async def _await_if_needed(value: Any) -> Any:
    """Await async Browser Use results while remaining friendly to test doubles."""
    if hasattr(value, "__await__"):
        return await value
    return value


async def open_url(url: str, browser_session: Any | None = None) -> dict[str, str]:
    """Open ``url`` in a new browser tab and return its target metadata."""
    if not url.strip():
        raise ValueError("url must not be empty")
    session = browser_session or connect_browser_harness()
    page = await _await_if_needed(cast(Any, session).new_page(url.strip()))
    return {
        "target_id": str(getattr(page, "target_id", "")),
        "title": str(await _await_if_needed(cast(Any, page).get_title()) or ""),
        "url": str(await _await_if_needed(cast(Any, page).get_url()) or ""),
    }


async def click_selector(
    selector: str,
    *,
    browser_session: Any | None = None,
) -> dict[str, str]:
    """Click exactly one CSS-selected element on the current browser page."""
    if not selector.strip():
        raise ValueError("selector must not be empty")
    session = browser_session or connect_browser_harness()
    page = await _await_if_needed(cast(Any, session).get_current_page())
    if page is None:
        raise RuntimeError("No active browser page is available")
    elements = await _await_if_needed(cast(Any, page).get_elements_by_css_selector(selector.strip()))
    if len(elements) != 1:
        raise LookupError(f"CSS selector matched {len(elements)} elements; expected exactly one")
    await _await_if_needed(cast(Any, elements[0]).click())
    return {
        "title": str(await _await_if_needed(cast(Any, page).get_title()) or ""),
        "url": str(await _await_if_needed(cast(Any, page).get_url()) or ""),
    }


async def screenshot(
    output_path: str | Path,
    *,
    browser_session: Any | None = None,
) -> Path:
    """Capture the current page as PNG and write it to ``output_path``."""
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    session = browser_session or connect_browser_harness()
    page = await _await_if_needed(cast(Any, session).get_current_page())
    if page is None:
        raise RuntimeError("No active browser page is available")
    image = await _await_if_needed(cast(Any, page).screenshot(format="png"))
    try:
        data = base64.b64decode(image, validate=True)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Browser Use returned an invalid PNG screenshot") from exc
    path.write_bytes(data)
    return path
