"""Regression tests for JobPilot's production safety boundaries."""

from browser_agent.jobpilot.application import build_application_report_from_result


def test_saved_without_verification_is_blocked() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="The application was saved.",
    )
    assert report.status == "blocked"
    assert report.metadata["verification_signal"] is False


def test_upload_verification_is_completion_signal() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="Resume upload verified; filename visible.",
    )
    assert report.status == "completed"
    assert report.metadata["verification_signal"] is True
