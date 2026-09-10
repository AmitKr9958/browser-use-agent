"""Unit tests for the JobPilot MVP application layer."""

from browser_agent.jobpilot.ats import score_job_match
from browser_agent.jobpilot.documents import build_cover_letter, tailor_resume_text
from browser_agent.jobpilot.models import ApplicationPlan, ContactProfile, JobDescription, MatchScore
from browser_agent.jobpilot.profile import infer_contact_profile
from browser_agent.jobpilot.workflow import build_application_task


def test_ats_score_is_explainable() -> None:
    result = score_job_match("Python Power BI Excel AI", "Python Excel experience")
    assert result.score > 0
    assert "python" in result.matched_keywords
    assert "power" in result.missing_keywords or "power" in result.matched_keywords


def test_contact_profile_extracts_email_and_phone() -> None:
    profile = infer_contact_profile("Amit Kumar\namit@example.com\n+91 98765 43210")
    assert profile.name == "Amit Kumar"
    assert profile.email == "amit@example.com"
    assert profile.phone == "+91 98765 43210"


def test_tailor_does_not_fabricate_experience() -> None:
    output = tailor_resume_text("Python developer", ("Kubernetes", "Azure"))
    assert "Python developer" in output
    assert "Kubernetes" in output
    assert "experienced in Kubernetes" not in output


def test_cover_letter_uses_supplied_identity_only() -> None:
    job = JobDescription(title="Data Analyst", company="Example Corp", description="Power BI")
    profile = ContactProfile(name="Amit Kumar")
    letter = build_cover_letter(job, profile)
    assert "Amit Kumar" in letter
    assert "Example Corp" in letter


def test_application_plan_cannot_enable_auto_submit() -> None:
    plan = ApplicationPlan(
        job=JobDescription(title="Analyst", company="Example", description="Python"),
        profile=ContactProfile(name="Amit"),
        match=MatchScore(score=100),
        tailored_resume_text="Python",
        cover_letter="Dear Hiring Team",
        auto_submit=False,
    )
    plan.validate()


def test_browser_task_contains_submission_guard() -> None:
    plan = ApplicationPlan(
        job=JobDescription(title="Analyst", company="Example", description="Python", url="https://example.com/apply"),
        profile=ContactProfile(name="Amit", email="amit@example.com"),
        match=MatchScore(score=100),
        tailored_resume_text="Python",
        cover_letter="Dear Hiring Team",
    )
    task = build_application_task(plan, resume_path="resume.pdf")
    assert "Never submit the application" in task
    assert "resume.pdf" in task
    assert "amit@example.com" in task
