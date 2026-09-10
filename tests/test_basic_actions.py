"""Tests for deterministic one-off browser actions."""

import base64
from pathlib import Path

import pytest

from browser_agent.actions.basic import click_selector, open_url, screenshot


class FakeElement:
    async def click(self) -> None:
        self.clicked = True


class FakePage:
    target_id = "target-1"

    def __init__(self) -> None:
        self.elements = [FakeElement()]
        self.url = "https://example.com"
        self.title = "Example"

    async def get_title(self) -> str:
        return self.title

    async def get_url(self) -> str:
        return self.url

    async def get_elements_by_css_selector(self, selector: str) -> list[FakeElement]:
        return self.elements if selector == "#submit" else []

    async def screenshot(self, format: str = "png") -> str:
        assert format == "png"
        return base64.b64encode(b"fake-png").decode()


class FakeSession:
    def __init__(self) -> None:
        self.page = FakePage()

    async def new_page(self, url: str) -> FakePage:
        self.page.url = url
        return self.page

    async def get_current_page(self) -> FakePage:
        return self.page


@pytest.mark.asyncio
async def test_open_url() -> None:
    result = await open_url("https://example.com", FakeSession())
    assert result == {"target_id": "target-1", "title": "Example", "url": "https://example.com"}


@pytest.mark.asyncio
async def test_click_requires_exactly_one_match() -> None:
    result = await click_selector("#submit", browser_session=FakeSession())
    assert result["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_click_rejects_missing_match() -> None:
    with pytest.raises(LookupError, match="matched 0 elements"):
        await click_selector(".missing", browser_session=FakeSession())


@pytest.mark.asyncio
async def test_screenshot_writes_png(tmp_path: Path) -> None:
    output = tmp_path / "page.png"
    result = await screenshot(output, browser_session=FakeSession())
    assert result == output
    assert output.read_bytes() == b"fake-png"
