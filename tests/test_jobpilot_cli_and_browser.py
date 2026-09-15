"""Regression tests for the live JobPilot CLI/browser integration."""

from types import SimpleNamespace

import pytest

from browser_agent.actions.basic import open_url
from browser_agent.jobpilot.cli import _load_inputs


class _FakePage:
    target_id = "target-1"

    async def get_title(self):
        return "Example"

    async def get_url(self):
        return "https://example.com/apply"


class _FakeSession:
    def __init__(self):
        self.started = False
        self.new_page_calls = 0

    async def start(self):
        self.started = True

    async def new_page(self, url):
        self.new_page_calls += 1
        assert self.started is True
        assert url == "https://example.com/apply"
        return _FakePage()


@pytest.mark.asyncio
async def test_open_url_starts_supplied_browser_session_before_new_page():
    session = _FakeSession()

    result = await open_url("https://example.com/apply", browser_session=session)

    assert session.started is True
    assert session.new_page_calls == 1
    assert result == {
        "target_id": "target-1",
        "title": "Example",
        "url": "https://example.com/apply",
    }


def test_load_inputs_accepts_inline_description(tmp_path):
    resume = tmp_path / "resume.txt"
    resume.write_text("Amit Kumar\namit@example.com\n+91 98765 43210", encoding="utf-8")
    args = SimpleNamespace(
        description="Python team lead role",
        resume=str(resume),
        profile="",
        memory="",
        title="Team Lead",
        company="Example Corp",
        url="https://example.com/apply",
    )

    job, resume_text, profile = _load_inputs(args)

    assert job.description == "Python team lead role"
    assert resume_text.startswith("Amit Kumar")
    assert profile.email == "amit@example.com"


def test_load_inputs_still_accepts_description_file(tmp_path):
    description = tmp_path / "job.txt"
    description.write_text("Excel and Power BI experience", encoding="utf-8")
    resume = tmp_path / "resume.txt"
    resume.write_text("Amit Kumar\namit@example.com", encoding="utf-8")
    args = SimpleNamespace(
        description=str(description),
        resume=str(resume),
        profile="",
        memory="",
        title="Analyst",
        company="Example Corp",
        url="https://example.com/apply",
    )

    job, _, _ = _load_inputs(args)

    assert job.description == "Excel and Power BI experience"
