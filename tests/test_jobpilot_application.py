"""Tests for structured JobPilot application reporting."""

import pytest

from browser_agent.jobpilot.application import ApplicationReport, build_application_report


def test_application_report_defaults_to_not_submitted() -> None:
    report = build_application_report(
        status="completed",
        target_url="https://example.com/apply",
        filled_fields=["email", "phone"],
    )
    assert report.submitted is False
    assert report.status == "completed"
    assert report.filled_fields == ("email", "phone")


def test_application_report_rejects_submission() -> None:
    with pytest.raises(ValueError, match="never mark"):
        ApplicationReport(
            status="completed",
            target_url="https://example.com/apply",
            submitted=True,
        ).validate()


def test_application_report_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="invalid application status"):
        build_application_report(status="submitted", target_url="https://example.com/apply")
