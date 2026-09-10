"""Tests for deterministic ATS resume quality checks."""

from jobpilot import ResumeProfile
from jobpilot.resume_quality import validate_ats_resume


def test_valid_resume_contains_core_contact_facts() -> None:
    profile = ResumeProfile(name="Amit Kumar", email="amit@example.com")
    result = validate_ats_resume("# Amit Kumar\namit@example.com\n\n## Skills\nPython", profile)
    assert result.valid is True
    assert result.errors == ()


def test_invalid_resume_rejects_tables_and_missing_email() -> None:
    profile = ResumeProfile(name="Amit Kumar", email="amit@example.com")
    result = validate_ats_resume("# Amit Kumar\n| Skills |\n| Python |", profile)
    assert result.valid is False
    assert "candidate email is missing" in result.errors
    assert "markdown table syntax is not ATS-safe" in result.errors
