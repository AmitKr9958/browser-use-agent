"""Tests for evidence-first career-site questionnaire handling."""

from browser_agent.jobpilot.models import ContactProfile
from browser_agent.jobpilot.questionnaire import answer_application_question, build_questionnaire_policy


def test_skill_question_answers_yes_from_resume() -> None:
    decision = answer_application_question(
        "Do you have experience with Power BI?",
        profile=ContactProfile(),
        resume_text="Senior BI Analyst with Power BI and DAX experience.",
    )
    assert decision.answer == "Yes"
    assert decision.confidence == "high"


def test_unknown_personal_question_is_not_guessed() -> None:
    decision = answer_application_question(
        "Are you willing to relocate?",
        profile=ContactProfile(),
        resume_text="Senior BI Analyst with Power BI experience.",
    )
    assert decision.answer is None


def test_work_authorization_uses_explicit_profile_value() -> None:
    decision = answer_application_question(
        "Are you legally authorized to work?",
        profile=ContactProfile(work_authorization="Yes"),
        resume_text="",
    )
    assert decision.answer == "Yes"


def test_sponsorship_uses_explicit_profile_value() -> None:
    decision = answer_application_question(
        "Will you require visa sponsorship?",
        profile=ContactProfile(sponsorship="No"),
        resume_text="",
    )
    assert decision.answer == "No"


def test_contact_question_uses_profile() -> None:
    decision = answer_application_question(
        "What is your LinkedIn URL?",
        profile=ContactProfile(linkedin="https://linkedin.example/profile"),
        resume_text="",
    )
    assert decision.answer == "https://linkedin.example/profile"


def test_questionnaire_policy_forbids_guessing() -> None:
    policy = build_questionnaire_policy()
    assert "Never guess" in policy
    assert "notice period" in policy
    assert "demographic/EEO" in policy
