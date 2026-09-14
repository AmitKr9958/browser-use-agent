"""Security and correctness tests for JobPilot application reporting."""

import pytest

from browser_agent.jobpilot.application import ApplicationReport, build_application_report, build_application_report_from_result


def test_application_report_defaults_to_not_submitted() -> None:
    report = build_application_report(
        status="completed",
        target_url="https://example.com/apply",
        filled_fields=["email", "phone"],
        metadata={"verification_signal": True},
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
            metadata={"verification_signal": True},
        ).validate()


def test_application_report_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="invalid application status"):
        build_application_report(status="submitted", target_url="https://example.com/apply")


def test_application_report_requires_target_url() -> None:
    with pytest.raises(ValueError, match="target_url"):
        build_application_report(status="blocked", target_url="")


def test_application_report_completed_requires_verification() -> None:
    with pytest.raises(ValueError, match="explicit verification"):
        build_application_report(status="completed", target_url="https://example.com/apply")


def test_result_with_explicit_verification_is_completed() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="Email field value verified and filename visible after upload.",
    )
    assert report.status == "completed"
    assert report.submitted is False
    assert report.metadata["verification_signal"] is True


def test_generic_filled_language_is_not_completion() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="I filled the name and email fields.",
    )
    assert report.status == "blocked"
    assert report.metadata["verification_signal"] is False


def test_result_with_submission_signal_is_never_reported_successfully() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="Application submitted successfully.",
    )
    assert report.status == "failed"
    assert report.submitted is False
    assert report.metadata["submission_signal"] is True


def test_result_with_captcha_is_blocked() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="Stopped because a CAPTCHA appeared.",
    )
    assert report.status == "blocked"
    assert "captcha" in report.blockers


def test_unverified_result_is_not_claimed_as_completed() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="I interacted with the form.",
    )
    assert report.status == "blocked"
    assert report.metadata["verification_signal"] is False


def test_review_instruction_is_not_itself_verification() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="Review required before continuing.",
    )
    assert report.status == "blocked"
    assert report.metadata["verification_signal"] is False


def test_empty_result_is_failed() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="   ",
    )
    assert report.status == "failed"
    assert report.metadata["verification_signal"] is False


def test_sensitive_values_are_redacted_from_raw_result() -> None:
    report = build_application_report_from_result(
        target_url="https://example.com/apply",
        raw_result="field value verified for amit@example.com, phone +91 98765 43210",
    )
    assert "amit@example.com" not in report.raw_result
    assert "98765 43210" not in report.raw_result
