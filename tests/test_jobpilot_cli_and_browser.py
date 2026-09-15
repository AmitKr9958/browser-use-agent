"""Regression tests for the live JobPilot CLI/browser integration."""

from types import SimpleNamespace

import pytest

from browser_use import ChatGoogle, ChatOpenAI

from browser_agent.actions.basic import open_url
from browser_agent.agents.agent import _build_primary_llm
from browser_agent.jobpilot.cli import _load_inputs
from browser_agent.jobpilot.models import ApplicationPlan, ContactProfile, JobDescription
from browser_agent.jobpilot.ats import score_job_match
from browser_agent.jobpilot.workflow import build_application_task


class _FakePage:
    target_id = "target-1"

    async def get_title(self):
        return "Example"

    async def get_url(self):
        return "https://example.com/apply"


class _PrivateTargetPage:
    _target_id = "target-private-1"

    async def get_title(self):
        return "Example"

    async def get_url(self):
        return "https://example.com/apply"


class _FakeSession:
    def __init__(self, page=None):
        self.started = False
        self.new_page_calls = 0
        self.page = page or _FakePage()

    async def start(self):
        self.started = True

    async def new_page(self, url):
        self.new_page_calls += 1
        assert self.started is True
        assert url == "https://example.com/apply"
        return self.page


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


@pytest.mark.asyncio
async def test_open_url_uses_browser_use_private_target_identity():
    session = _FakeSession(page=_PrivateTargetPage())

    result = await open_url("https://example.com/apply", browser_session=session)

    assert result["target_id"] == "target-private-1"


@pytest.mark.asyncio
async def test_open_url_falls_back_to_current_target_info():
    class _NoTargetPage:
        async def get_title(self):
            return "Example"

        async def get_url(self):
            return "https://example.com/apply"

    class _CurrentTargetSession(_FakeSession):
        def __init__(self):
            super().__init__(page=_NoTargetPage())

        async def get_current_target_info(self):
            return {"targetId": "target-current-1"}

    session = _CurrentTargetSession()

    result = await open_url("https://example.com/apply", browser_session=session)

    assert result["target_id"] == "target-current-1"


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


def test_application_task_contains_generated_cover_letter_and_resume_path():
    job = JobDescription(
        title="Team Lead",
        company="Example Corp",
        description="Python team lead role",
        url="https://example.com/apply",
    )
    profile = ContactProfile(name="Amit Kumar", email="amit@example.com", phone="+91 98765 43210")
    plan = ApplicationPlan(
        job=job,
        profile=profile,
        match=score_job_match(job.description, "Amit Kumar Python team lead"),
        tailored_resume_text="Amit Kumar Python team lead",
        cover_letter="Dear Hiring Team,\nI am interested in this Team Lead role.",
        answers={},
        auto_submit=False,
    )

    task = build_application_task(plan, resume_path="C:\\Resume\\Amit.docx")

    assert "Resume file: C:\\Resume\\Amit.docx" in task
    assert "SUPPLIED GENERATED COVER LETTER" in task
    assert "Dear Hiring Team" in task
    assert "Never submit the application." in task


def test_primary_llm_uses_9router_when_key_is_configured(monkeypatch):
    monkeypatch.setenv("NINEROUTER_API_KEY", "test-router-key")
    monkeypatch.setenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1")
    monkeypatch.setenv("NINEROUTER_MODEL", "qwen-test")

    llm = _build_primary_llm("gemini-3.6-flash")

    assert isinstance(llm, ChatOpenAI)
    assert getattr(llm, "model_name", None) == "qwen-test"
    assert "localhost:20128/v1" in str(getattr(llm, "openai_api_base", ""))


def test_primary_llm_keeps_gemini_without_9router_key(monkeypatch):
    monkeypatch.delenv("NINEROUTER_API_KEY", raising=False)
    llm = _build_primary_llm("gemini-3.6-flash")
    assert isinstance(llm, ChatGoogle)
