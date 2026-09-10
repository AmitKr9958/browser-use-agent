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
from .documents import build_cover_letter, tailor_resume_text
from .models import ApplicationPlan, ContactProfile, JobDescription


def build_application_task(plan: ApplicationPlan, *, resume_path: str) -> str:
    """Build a conservative Browser Use task that fills but never submits."""
    plan.validate()
    contact = plan.job
    answers = "\n".join(f"- {key}: {value}" for key, value in plan.answers.items()) or "- No extra answers supplied."
    return f"""
You are JobPilot, a job-application assistant.

Target role: {contact.title} at {contact.company}
Application URL: {contact.url}
Resume file: {resume_path}

OBJECTIVE
1. Inspect the currently open application page and identify all visible application fields.
2. Fill only fields for which a value is explicitly supplied below or is directly supported by the resume.
3. Upload the supplied resume when a resume/CV upload control exists.
4. If a question is ambiguous, sensitive, demographic, legal, sponsorship-related, salary-related, or requires a value not supplied, leave it unchanged and report it for manual review.
5. Verify filled values after interaction where the page permits.
6. STOP before clicking any final Submit, Apply, Send, Complete application, or equivalent submission control.

CONTACT DATA
- Name: {plan.job.company and 'Use the supplied profile name in the runtime context; do not invent one.'}
- Additional answers:
{answers}

RESUME/ATS CONTEXT
Matched keywords: {', '.join(plan.match.matched_keywords) or 'none'}
Missing keywords for review only: {', '.join(plan.match.missing_keywords) or 'none'}

SAFETY
- Never invent personal information, employment history, education, dates, salary, authorization, sponsorship, identity numbers, passwords, OTPs, or demographic answers.
- Never submit the application.
- Stop at CAPTCHA, MFA/OTP, login, payment, or identity-verification steps and report the blocker.
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
        """Prepare ATS score and truthful document variants before browser actions."""
        match = score_job_match(job.description, resume_text)
        tailored = tailor_resume_text(resume_text, match.missing_keywords)
        cover_letter = build_cover_letter(job, profile, resume_text=resume_text)
        plan = ApplicationPlan(
            job=job,
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
        task = build_application_task(plan, resume_path=resume_path)
        return await run_on_tab(
            task,
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
            await open_url(plan.job.url, browser_session=session)
            return await run_on_tab(
                build_application_task(plan, resume_path=resume_path),
                TabSelector(index=0),
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
