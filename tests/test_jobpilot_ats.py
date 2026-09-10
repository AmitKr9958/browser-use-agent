"""Tests for JobPilot ATS and career-page primitives."""

from jobpilot.ats import ATS, detect_ats
from jobpilot.career_pages import CareerPage, CareerPageRegistry
from jobpilot.field_policy import is_safe_autofill_label


def test_detect_common_ats_from_url() -> None:
    assert detect_ats("https://boards.greenhouse.io/example/jobs/1") == ATS.GREENHOUSE
    assert detect_ats("https://jobs.lever.co/example/1") == ATS.LEVER
    assert detect_ats("https://example.wd5.myworkdayjobs.com/en-US/example") == ATS.WORKDAY
    assert detect_ats("https://jobs.ashbyhq.com/example/1") == ATS.ASHBY


def test_detect_custom_when_html_is_present() -> None:
    assert detect_ats("https://careers.example.com/apply", "<form><input name='email'></form>") == ATS.CUSTOM


def test_career_registry_matches_host_and_path() -> None:
    registry = CareerPageRegistry([CareerPage("Example", "https://careers.example.com/jobs", "custom")])
    assert registry.match_url("https://careers.example.com/jobs/123").company == "Example"
    assert registry.match_url("https://other.example.com/jobs/123") is None


def test_sensitive_fields_are_never_safe() -> None:
    assert is_safe_autofill_label("Email address") is True
    assert is_safe_autofill_label("Aadhaar Number") is False
    assert is_safe_autofill_label("OTP") is False
