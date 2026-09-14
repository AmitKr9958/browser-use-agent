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


def test_secret_assignment_is_fully_redacted_for_colon_and_equals() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="password=SuperSecret123 otp: 482901 email=amit@example.com phone=+91 98765 43210",
    )
    assert "SuperSecret123" not in report.raw_result
    assert "482901" not in report.raw_result
    assert "amit@example.com" not in report.raw_result
    assert "98765 43210" not in report.raw_result
    assert "[REDACTED]" in report.raw_result
    assert "[EMAIL REDACTED]" in report.raw_result
    assert "[PHONE REDACTED]" in report.raw_result


def test_otp_substring_does_not_create_false_blocker() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="The profile section was fields verified.",
    )
    assert report.status == "completed"
    assert report.metadata["verification_signal"] is True


def test_submission_signal_is_never_reported_as_completed() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="Application submitted successfully.",
    )
    assert report.status == "failed"
    assert report.metadata["submission_signal"] is True
    assert report.metadata["verification_signal"] is False
