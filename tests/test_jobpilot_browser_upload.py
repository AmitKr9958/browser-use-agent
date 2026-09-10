"""Tests for deterministic Browser Use file uploads."""

from pathlib import Path

import pytest

from jobpilot.browser_upload import upload_file_by_dom_index


class _Event:
    def __init__(self) -> None:
        self.awaited = False
        self.result_checked = False

    def __await__(self):
        async def _wait() -> None:
            self.awaited = True

        return _wait().__await__()

    async def event_result(self, **_: object) -> None:
        self.result_checked = True


class _Bus:
    def __init__(self, event: _Event) -> None:
        self.event = event

    def dispatch(self, event: object) -> _Event:
        self.dispatched = event
        return self.event


class _Session:
    def __init__(self, node: object | None) -> None:
        self.node = node
        self.event = _Event()
        self.event_bus = _Bus(self.event)

    async def get_element_by_index(self, index: int) -> object | None:
        self.index = index
        return self.node


@pytest.mark.asyncio
async def test_upload_dispatches_event_for_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "resume.pdf"
    path.write_text("resume", encoding="utf-8")
    session = _Session(object())

    await upload_file_by_dom_index(session, 4, path)

    assert session.index == 4
    assert session.event.awaited is True
    assert session.event.result_checked is True


@pytest.mark.asyncio
async def test_upload_rejects_missing_file(tmp_path: Path) -> None:
    session = _Session(object())
    with pytest.raises(FileNotFoundError):
        await upload_file_by_dom_index(session, 0, tmp_path / "missing.pdf")


@pytest.mark.asyncio
async def test_upload_rejects_missing_dom_node(tmp_path: Path) -> None:
    path = tmp_path / "resume.pdf"
    path.write_text("resume", encoding="utf-8")
    session = _Session(None)

    with pytest.raises(RuntimeError, match="DOM element"):
        await upload_file_by_dom_index(session, 0, path)
