"""Safe deterministic file-upload primitive for Browser Use application flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from browser_use.browser.events import UploadFileEvent


async def upload_file_by_dom_index(
    browser_session: Any,
    index: int,
    path: str | Path,
) -> None:
    """Upload a local file to a Browser Use DOM file-input index.

    This primitive never submits a form. The caller must explicitly identify the
    file-input DOM index, which prevents accidental uploads to unrelated controls.
    """
    if index < 0:
        raise ValueError("index must be non-negative")
    file_path = Path(path).expanduser().resolve()
    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    node = await browser_session.get_element_by_index(index)
    if node is None:
        raise RuntimeError(f"Browser Use DOM element {index} was not found")

    event = browser_session.event_bus.dispatch(
        UploadFileEvent(node=node, file_path=str(file_path))
    )
    await event
    await event.event_result(raise_if_any=True, raise_if_none=False)
