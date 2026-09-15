"""Deterministic dummy-application acceptance tests for JobPilot safety behavior."""

from pathlib import Path

from browser_agent.jobpilot.application import build_application_report_from_result
from browser_agent.jobpilot.cli import build_parser
from browser_agent.jobpilot.models import ApplicationPlan, ContactProfile, JobDescription, MatchScore
from browser_agent.jobpilot.workflow import build_application_task


FIXTURE = Path(__file__).parent / "fixtures" / "jobpilot_dummy_application.html"


def test_prepare_cli_has_bounded_default_step_budget() -> None:
    args = build_parser().parse_args(
        [
            "prepare",
            "--title",
            "Data Analyst",
            "--company",
            "Example India Pvt Ltd",
            "--description",
            "dummy.txt",
            "--resume",
            "dummy-resume.pdf",
        ]
    )
    assert args.max_steps == 80


def test_dummy_application_contains_expected_review_and_sensitive_fields() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    for field in ("name", "email", "phone", "resume", "salary", "authorized"):
        assert f'name="{field}"' in html
    assert "Continue" in html
    assert "Submit application" in html


def test_dummy_application_task_allows_progress_but_forbids_submission() -> None:
    plan = ApplicationPlan(
        job=JobDescription(
            title="Data Analyst",
            company="Example India Pvt Ltd",
            description="Python Excel Power BI",
            url="https://example.test/application",
        ),
        profile=ContactProfile(
            name="Test Candidate",
            email="test@example.com",
            phone="+91 98765 43210",
            location="Delhi",
        ),
        match=MatchScore(score=100),
        tailored_resume_text="Test Candidate\nPython\nExcel",
        cover_letter="Dear Hiring Team,\nI am interested in this role.",
    )
    task = build_application_task(plan, resume_path="dummy-resume.pdf")
    assert "safe Next" in task
    assert "Never submit the application" in task
    assert "STOP at the final Review/confirmation stage" in task
    assert "salary" in task.lower()
    assert "work_authorization" in task


def test_dummy_verified_result_is_completed_but_never_submitted() -> None:
    report = build_application_report_from_result(
        target_url="https://example.test/application",
        raw_result="Full name field value verified; filename visible; stopped at final review.",
    )
    assert report.status == "completed"
    assert report.metadata["verification_signal"] is True
    assert report.submitted is False


def test_dummy_submission_language_is_rejected() -> None:
    report = build_application_report_from_result(
        target_url="https://example.test/application",
        raw_result="Application submitted successfully.",
    )
    assert report.status == "failed"
    assert report.submitted is False
    assert report.metadata["submission_signal"] is True
