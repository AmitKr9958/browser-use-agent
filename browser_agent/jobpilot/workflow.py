"""JobPilot orchestration on top of the repository's Browser Use agent."""

from __future__ import annotations

import inspect
from typing import Any

from browser_agent.agents.agent import run_on_tab
from browser_agent.actions.basic import open_url
from browser_agent.connection.harness import connect_browser_harness
from browser_agent.models.india import DEFAULT_INDIA_RUNTIME
from browser_agent.models.policy import DEFAULT_SENSITIVE_POLICY
from browser_agent.tabs.models import TabSelector

from .ats import score_job_match
from .documents import (
    build_cover_letter,
    build_cover_letter_with_llm,
    tailor_resume_text,
    tailor_resume_with_llm,
)
from .models import ApplicationPlan, ContactProfile, JobDescription


def build_application_task(plan: ApplicationPlan, *, resume_path: str) -> str:
    """Build a conservative Browser Use task that fills but never submits."""
    plan.validate()
    answers = "\n".join(f"- {key}: {value}" for key, value in plan.answers.items()) or "- No extra answers supplied."
    profile = plan.profile
    supplied = {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin": profile.linkedin,
        "portfolio": profile.portfolio,
        "work_authorization": profile.work_authorization,
        "sponsorship": profile.sponsorship,
    }
    contact_lines = "\n".join(f"- {key}: {value or '[NOT SUPPLIED — leave blank]'}" for key, value in supplied.items())
    return f"""
You are JobPilot, a job-application assistant.

Target role: {plan.job.title} at {plan.job.company}
Application URL: {plan.job.url}
Resume file: {resume_path}

OBJECTIVE
1. Inspect the currently open application page and identify all visible application fields, including fields inside supported frames.
2. Fill only fields for which a value is explicitly supplied below or is directly supported by the resume.
3. Upload the supplied resume when a resume/CV upload control exists. After upload, verify the filename is visible or the control reports the file as attached.
4. For legal, sponsorship, salary, demographic, or other sensitive questions, fill only when the exact value is explicitly supplied and the question is unambiguous; otherwise leave unchanged and report it for manual review.
5. Verify filled values after interaction where the page permits.
6. STOP before clicking any final Submit, Apply, Send, Complete application, or equivalent submission control.

SUPPLIED PROFILE
{contact_lines}

ADDITIONAL ANSWERS
{answers}

RESUME/ATS CONTEXT
Matched keywords: {', '.join(plan.match.matched_keywords) or 'none'}
Missing keywords for review only: {', '.join(plan.match.missing_keywords) or 'none'}

SAFETY
- Never invent personal information, employment history, education, dates, salary, authorization, sponsorship, identity numbers, passwords, OTPs, or demographic answers.
- Never submit the application.
- Stop at CAPTCHA, MFA/OTP, login, payment, or identity-verification steps and report the blocker.
- If no form fields are exposed, report the page state and do not claim autofill succeeded.
- Do not claim success unless the field interaction or upload is visibly verified.
""".strip()


class JobPilot:
    """High-level JobPilot workflow using the existing Browser Use/Harness stack."""

    def __init__(self, *, model: str = "gemini-3.6-flash", max_steps: int = 80) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.model = model
        self.max_steps = max_steps

    def prepare_plan(
        self,
        job: JobDescription,
        resume_text: str,
        profile: ContactProfile,
        *,
        answers: dict[str, str] | None = None,
    ) -> ApplicationPlan:
        """Prepare deterministic ATS score and safe document variants."""
        match = score_job_match(job.description, resume_text)
        tailored = tailor_resume_text(resume_text, match.missing_keywords)
        cover_letter = build_cover_letter(job, profile, resume_text=resume_text)
        plan = ApplicationPlan(
            job=job,
            profile=profile,
            match=match,
            tailored_resume_text=tailored,
            cover_letter=cover_letter,
            answers=dict(answers or {}),
            auto_submit=False,
        )
        plan.validate()
        return plan

    async def prepare_plan_async(
        self,
        job: JobDescription,
        resume_text: str,
        profile: ContactProfile,
        *,
        answers: dict[str, str] | None = None,
        use_llm: bool = True,
    ) -> ApplicationPlan:
        """Prepare an ATS score plus LLM drafts, falling back safely when unavailable."""
        match = score_job_match(job.description, resume_text)
        tailored = tailor_resume_text(resume_text, match.missing_keywords)
        cover_letter = build_cover_letter(job, profile, resume_text=resume_text)
        if use_llm:
            try:
                tailored = await tailor_resume_with_llm(resume_text, job.description, model=self.model)
            except Exception:
                tailored = tailor_resume_text(resume_text, match.missing_keywords)
            try:
                cover_letter = await build_cover_letter_with_llm(job, profile, resume_text, model=self.model)
            except Exception:
                cover_letter = build_cover_letter(job, profile, resume_text=resume_text)
        plan = ApplicationPlan(
            job=job,
            profile=profile,
            match=match,
            tailored_resume_text=tailored,
            cover_letter=cover_letter,
            answers=dict(answers or {}),
            auto_submit=False,
        )
        plan.validate()
        return plan

    async def apply_to_open_page(self, plan: ApplicationPlan, *, resume_path: str) -> Any:
        """Fill the already-open application page and stop before submission."""
        return await run_on_tab(
            build_application_task(plan, resume_path=resume_path),
            TabSelector(index=0),
            model=self.model,
            max_steps=self.max_steps,
            india_runtime=DEFAULT_INDIA_RUNTIME,
            interaction_policy=DEFAULT_SENSITIVE_POLICY,
        )

    async def apply_to_url(self, plan: ApplicationPlan, *, resume_path: str) -> Any:
        """Open a supplied application URL, then perform controlled autofill."""
        if not plan.job.url.strip():
            raise ValueError("job application URL must be supplied")
        session = connect_browser_harness()
        try:
            opened = await open_url(plan.job.url, browser_session=session)
            target_id = opened.get("target_id", "").strip()
            if not target_id:
                raise RuntimeError("Browser did not return a target id for the application page")
            return await run_on_tab(
                build_application_task(plan, resume_path=resume_path),
                TabSelector(target_id=target_id),
                model=self.model,
                browser_session=session,
                max_steps=self.max_steps,
                india_runtime=DEFAULT_INDIA_RUNTIME,
                interaction_policy=DEFAULT_SENSITIVE_POLICY,
            )
        finally:
            stop = getattr(session, "stop", None)
            if callable(stop):
                result = stop()
                if inspect.isawaitable(result):
                    await result
