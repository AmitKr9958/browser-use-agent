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


async def _ensure_session_started(session: Any) -> Any:
    """Start a Browser Use session before using CDP-backed page operations."""
    start = getattr(session, "start", None)
    if callable(start):
        await _await_if_needed(start())
    return session


async def open_url(url: str, browser_session: Any | None = None) -> dict[str, str]:
    """Open ``url`` in a new browser tab and return stable target metadata."""
    if not url.strip():
        raise ValueError("url must not be empty")
    session = await _ensure_session_started(browser_session or connect_browser_harness())
    page = await _await_if_needed(cast(Any, session).new_page(url.strip()))

    # Browser Use's actor Page intentionally keeps the target identity private
    # (`_target_id`). Older/newer wrappers may expose `target_id` publicly, so
    # prefer the public attribute and fall back to the stable actor identity.
    target_id = str(getattr(page, "target_id", "") or getattr(page, "_target_id", ""))
    if not target_id:
        # As a final compatibility fallback, ask the session for its current
        # target information. This avoids inventing an identifier.
        get_current_target_info = getattr(session, "get_current_target_info", None)
        if callable(get_current_target_info):
            info = await _await_if_needed(get_current_target_info())
            if isinstance(info, dict):
                target_id = str(info.get("targetId", "") or info.get("target_id", ""))

    return {
        "target_id": target_id,
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
    session = await _ensure_session_started(browser_session or connect_browser_harness())
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
    session = await _ensure_session_started(browser_session or connect_browser_harness())
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
