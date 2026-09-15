"""Deterministic one-off browser actions for the command-line interface."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, cast

from browser_agent.connection.session_manager import BrowserSessionManager
from browser_agent.utils import await_if_needed


async def _ensure_session_started(session: Any) -> Any:
    """Backward-compatible helper that ensures a supplied session is initialized."""
    async with BrowserSessionManager(session):
        return session


def _target_id_from_session(session: Any) -> str:
    value = getattr(session, "_target_id", None)
    return value.strip() if isinstance(value, str) else ""


def _target_id_from_page(page: Any) -> str:
    for attribute in ("target_id", "_target_id"):
        value = getattr(page, attribute, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def open_url(url: str, browser_session: Any | None = None) -> dict[str, str]:
    """Open ``url`` in a new browser tab and return stable target metadata."""
    if not url.strip():
        raise ValueError("url must not be empty")
    async with BrowserSessionManager(browser_session) as session:
        session = await _ensure_session_started(session)
        page = await await_if_needed(cast(Any, session).new_page(url.strip()))
        target_id = _target_id_from_session(session) or _target_id_from_page(page)
        if not target_id:
            get_current_target_info = getattr(session, "get_current_target_info", None)
            if callable(get_current_target_info):
                info = await await_if_needed(get_current_target_info())
                if isinstance(info, dict):
                    for key in ("targetId", "target_id", "id"):
                        value = info.get(key)
                        if isinstance(value, str) and value.strip():
                            target_id = value.strip()
                            break
        return {
            "target_id": target_id,
            "title": str(await await_if_needed(cast(Any, page).get_title()) or ""),
            "url": str(await await_if_needed(cast(Any, page).get_url()) or ""),
        }


async def click_selector(selector: str, *, browser_session: Any | None = None) -> dict[str, str]:
    """Click exactly one CSS-selected element on the current browser page."""
    if not selector.strip():
        raise ValueError("selector must not be empty")
    async with BrowserSessionManager(browser_session) as session:
        session = await _ensure_session_started(session)
        page = await await_if_needed(cast(Any, session).get_current_page())
        if page is None:
            raise RuntimeError("No active browser page is available")
        elements = await await_if_needed(cast(Any, page).get_elements_by_css_selector(selector.strip()))
        if len(elements) != 1:
            raise LookupError(f"CSS selector matched {len(elements)} elements; expected exactly one")
        await await_if_needed(cast(Any, elements[0]).click())
        return {
            "title": str(await await_if_needed(cast(Any, page).get_title()) or ""),
            "url": str(await await_if_needed(cast(Any, page).get_url()) or ""),
        }


async def screenshot(output_path: str | Path, *, browser_session: Any | None = None) -> Path:
    """Capture the current page as PNG and write it to ``output_path``."""
    path = Path(output_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with BrowserSessionManager(browser_session) as session:
        session = await _ensure_session_started(session)
        page = await await_if_needed(cast(Any, session).get_current_page())
        if page is None:
            raise RuntimeError("No active browser page is available")
        image = await await_if_needed(cast(Any, page).screenshot(format="png"))
        try:
            data = base64.b64decode(image, validate=True)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("Browser Use returned an invalid PNG screenshot") from exc
        path.write_bytes(data)
    return path
