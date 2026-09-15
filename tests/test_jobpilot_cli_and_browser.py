from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from browser_agent.actions.basic import click_selector, open_url, screenshot
from browser_agent.agents.agent import _build_primary_llm
from browser_agent.connection.harness import start_browser_harness_session
from browser_agent.jobpilot.cli import _load_inputs
from browser_agent.jobpilot.workflow import build_application_task
from browser_use import Agent, BrowserSession, ChatGoogle, ChatOpenAI


@pytest.mark.asyncio
async def test_open_url_starts_supplied_browser_session_before_new_page(monkeypatch):
    session = BrowserSession()
    session.start = AsyncMock()
    page = AsyncMock()
    page.url = "https://example.com"
    session.new_page = AsyncMock(return_value=page)
    session._target_id = "target-123"

    monkeypatch.setattr("browser_agent.actions.basic._ensure_session_started", AsyncMock())

    result = await open_url(session, "https://example.com")

    session.new_page.assert_awaited_once_with("https://example.com")
    assert result["url"] == "https://example.com"
    assert result["target_id"] == "target-123"


@pytest.mark.asyncio
async def test_open_url_uses_browser_use_private_target_identity(monkeypatch):
    session = BrowserSession()
    session._target_id = "private-target"
    page = AsyncMock()
    page.url = "https://example.com"
    session.new_page = AsyncMock(return_value=page)
    monkeypatch.setattr("browser_agent.actions.basic._ensure_session_started", AsyncMock())

    result = await open_url(session, "https://example.com")

    assert result["target_id"] == "private-target"


@pytest.mark.asyncio
async def test_open_url_falls_back_to_current_target_info(monkeypatch):
    session = BrowserSession()
    page = AsyncMock()
    page.url = "https://example.com"
    session.new_page = AsyncMock(return_value=page)
    session._target_id = None
    session.get_current_target_info = AsyncMock(return_value={"target_id": "fallback-target"})
    monkeypatch.setattr("browser_agent.actions.basic._ensure_session_started", AsyncMock())

    result = await open_url(session, "https://example.com")

    assert result["target_id"] == "fallback-target"


def test_load_inputs_accepts_inline_description(tmp_path):
    args = type("Args", (), {
        "description": "Inline job description",
        "description_file": None,
        "resume": str(tmp_path / "resume.docx"),
        "url": "https://example.com/job",
    })()
    result = _load_inputs(args)
    assert result["description"] == "Inline job description"


def test_load_inputs_still_accepts_description_file(tmp_path):
    description_file = tmp_path / "description.txt"
    description_file.write_text("File job description", encoding="utf-8")
    args = type("Args", (), {
        "description": str(description_file),
        "description_file": None,
        "resume": str(tmp_path / "resume.docx"),
        "url": "https://example.com/job",
    })()
    result = _load_inputs(args)
    assert result["description"] == "File job description"


def test_application_task_contains_generated_cover_letter_and_resume_path():
    plan = type("Plan", (), {
        "job_description": "Python developer",
        "cover_letter": "Dear Hiring Team",
        "auto_submit": False,
    })()

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
    assert "localhost:20128/v1" in str(getattr(llm, "base_url", ""))


def test_primary_llm_keeps_gemini_without_9router_key(monkeypatch):
    monkeypatch.delenv("NINEROUTER_API_KEY", raising=False)
    llm = _build_primary_llm("gemini-3.6-flash")
    assert isinstance(llm, ChatGoogle)
