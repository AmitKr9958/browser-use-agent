"""Deterministic tests for vendor-independent career-form heuristics."""

from browser_agent.jobpilot.form_compat import (
    build_universal_form_policy,
    classify_field,
    detect_ats_family,
    is_final_submission_control,
    is_sensitive_field,
)


def test_common_career_field_labels_are_classified() -> None:
    assert classify_field("First Name") == "name"
    assert classify_field("Legal Name") == "name"
    assert classify_field("Preferred Name") == "name"
    assert classify_field("Email address") == "email"
    assert classify_field("Mobile / Telephone") == "phone"
    assert classify_field("Address Line 1") == "location"
    assert classify_field("State / Province") == "location"
    assert classify_field("LinkedIn Profile URL") == "linkedin"
    assert classify_field("GitHub Profile") == "portfolio"
    assert classify_field("Upload CV / Resume") == "resume"
    assert classify_field("Cover Letter or Motivation") == "cover_letter"


def test_sensitive_questions_are_never_treated_as_ordinary_fields() -> None:
    for label in (
        "PAN Number",
        "Aadhaar",
        "Passport Number",
        "Expected Salary",
        "Notice Period",
        "Work Authorization",
        "Visa Sponsorship",
        "Date of Birth",
        "Government ID",
        "OTP",
    ):
        assert is_sensitive_field(label) is True


def test_final_submission_controls_are_detected() -> None:
    for label in (
        "Submit Application",
        "Apply Now",
        "Send Application",
        "Complete Application",
        "Finish Application",
        "Finalize Application",
    ):
        assert is_final_submission_control(label) is True
    assert is_final_submission_control("Save and Continue") is False
    assert is_final_submission_control("Next") is False


def test_known_ats_families_are_detected_without_vendor_selectors() -> None:
    assert detect_ats_family("https://boards.greenhouse.io/example/jobs/1") == "greenhouse"
    assert detect_ats_family("https://jobs.lever.co/example/abc") == "lever"
    assert detect_ats_family("https://example.myworkdayjobs.com/en-US/careers/job/1") == "workday"
    assert detect_ats_family("https://apply.workable.com/example/j/123/") == "workable"
    assert detect_ats_family("https://example.com/careers/apply") == "generic"
    assert detect_ats_family("https://EXAMPLE.COM./careers/apply") == "generic"


def test_universal_policy_requires_rescan_verification_and_safe_navigation() -> None:
    policy = build_universal_form_policy("https://apply.workable.com/example/j/123")
    assert "workable" in policy
    assert "Re-scan" in policy
    assert "accessible names" in policy
    assert "Never click a control classified as final submission" in policy
    assert "unresolved mandatory sensitive/unknown question" in policy
    assert "verification" in policy.lower()
