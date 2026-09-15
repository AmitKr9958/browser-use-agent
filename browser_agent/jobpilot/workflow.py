"""JobPilot orchestration on top of the repository's Browser Use agent."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from browser_agent.actions.basic import open_url
from browser_agent.agents.agent import run_on_tab
from browser_agent.connection.harness import connect_browser_harness
from browser_agent.models.india import DEFAULT_INDIA_RUNTIME
from browser_agent.models.policy import DEFAULT_SENSITIVE_POLICY
from browser_agent.tabs.models import TabSelector

from .ats import score_job_match
from .documents import build_cover_letter, build_cover_letter_with_llm, tailor_resume_text, tailor_resume_with_llm
from .form_compat import build_universal_form_policy
from .models import ApplicationPlan, ContactProfile, JobDescription
from .questionnaire import build_questionnaire_policy


def _validate_web_url(url: str, *, field_name: str) -> None:
    """Require a syntactically valid HTTP(S) URL before handing it to a browser."""
    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be a valid http(s) URL")


def build_application_task(plan: ApplicationPlan, *, resume_path: str) -> str:
    """Build a conservative, vendor-independent Browser Use task that fills but never submits."""
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
You are JobPilot, a production-grade job-application assistant.

Target role: {plan.job.title} at {plan.job.company}
Application URL: {plan.job.url}
Resume file: {resume_path}

OBJECTIVE
1. Inspect the complete currently open application workflow and identify every visible application field, including fields in supported frames and web components.
2. Fill only fields for which a value is explicitly supplied below or is directly supported by the supplied resume.
3. Use accessible names, visible labels, placeholders, surrounding question text and actual control state. Never depend on a vendor's element IDs, class names, field order, or brittle selectors.
4. Handle native inputs, custom comboboxes, autocomplete fields, radio groups, checkboxes, date controls, rich-text editors, and file-upload controls using real user-like interaction. Verify the resulting value/state after each interaction.
5. Upload the supplied resume when a resume/CV upload control exists. Verify the selected filename or attached-file state. Do not upload any other file unless explicitly supplied.
6. If a cover-letter/motivation field exists, fill it only with the supplied generated cover letter. Verify the resulting text/state.
7. For multi-step application wizards, safely use Next, Continue, Save, or Save and Continue only when the control is clearly non-final. Re-scan the newly rendered page after every transition.
8. Automatically answer ordinary career-site questions only when the questionnaire policy below establishes an explicit evidence-backed answer.
9. For legal, sponsorship, salary, demographic, identity, compensation, consent, or other sensitive questions, fill only when the exact value is explicitly supplied and the question is unambiguous; otherwise leave unchanged and report it for manual review.
10. If a mandatory question cannot be answered from supplied evidence, stop at that step and report the exact question rather than guessing.
11. STOP at the final Review/confirmation stage and before clicking any final Submit, Apply, Send, Complete application, Finish application, or equivalent control.

SUPPLIED PROFILE
{contact_lines}

ADDITIONAL ANSWERS
{answers}

RESUME/ATS CONTEXT
Matched keywords: {', '.join(plan.match.matched_keywords) or 'none'}
Missing keywords for review only: {', '.join(plan.match.missing_keywords) or 'none'}

{build_universal_form_policy(plan.job.url)}

{build_questionnaire_policy()}

FINAL ACCEPTANCE REPORT
Return a concise structured report containing:
- final page/step reached
- each field filled and whether its value/state was verified
- each skipped field and exact reason
- resume upload verification
- cover-letter verification
- any blocker (CAPTCHA, login, MFA/OTP, payment, identity verification, unsupported control, inaccessible frame, etc.)
- whether a final submission control was found and left untouched
- overall status: COMPLETED_REVIEW_READY, BLOCKED_MANUAL_REVIEW, or FAILED_VERIFICATION

SAFETY
- Never invent personal information, employment history, education, dates, salary, authorization, sponsorship, identity numbers, passwords, OTPs, or demographic answers.
- Never submit the application.
- Never click a final submission control even if the page says it is required to finish.
- Stop at CAPTCHA, MFA/OTP, login, payment, or identity-verification steps and report the blocker.
- If no form fields are exposed, report the page state and do not claim autofill succeeded.
- Do not claim success unless field interactions and uploads are visibly verified.
""".strip()


def build_job_extraction_task(url: str) -> str:
    """Build a read-only browser task that extracts the public job posting."""
    _validate_web_url(url, field_name="job URL")
    return f"""
Open and inspect the public job posting at {url}.
Do not click Apply, Submit, Send, Continue into an application, or perform any login.
Return ONLY valid JSON with these string fields: title, company, location, description.
Use the actual visible job posting text. Put responsibilities, required skills, preferred skills, experience, education and other relevant requirements into description.
Do not invent missing facts. If a field is not visible, return an empty string.
""".strip()


def _history_text(history: Any) -> str:
    final_result = getattr(history, "final_result", None)
    if callable(final_result):
        return str(final_result())
    return str(history)


def _parse_job_description_result(raw: str, *, url: str, fallback: JobDescription) -> JobDescription:
    """Parse the agent's JSON result without accepting fabricated non-JSON prose."""
    text = raw.strip()
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("job description extractor did not return JSON")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ValueError("job description extractor returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("job description extractor returned a non-object")
    title = str(data.get("title", "")).strip()
    company = str(data.get("company", "")).strip()
    location = str(data.get("location", "")).strip()
    description = str(data.get("description", "")).strip()
    if not title or not company or not description:
        raise ValueError("job description extractor returned incomplete job data")
    return JobDescription(title=title, company=company, description=description, url=url, location=location)


async def extract_job_description_from_url(url: str, *, model: str = "gemini-3.6-flash", max_steps: int = 40) -> JobDescription:
    """Read a public job URL and return a validated normalized JobDescription."""
    _validate_web_url(url, field_name="job URL")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    session = connect_browser_harness()
    try:
        opened = await open_url(url, browser_session=session)
        target_id = opened.get("target_id", "").strip()
        if not target_id:
            raise RuntimeError("Browser did not return a target id for the job page")
        history = await run_on_tab(
            build_job_extraction_task(url),
            TabSelector(target_id=target_id),
            model=model,
            browser_session=session,
            max_steps=max_steps,
            india_runtime=DEFAULT_INDIA_RUNTIME,
            interaction_policy=DEFAULT_SENSITIVE_POLICY,
        )
        return _parse_job_description_result(_history_text(history), url=url, fallback=JobDescription(title="", company="", description="", url=url))
    finally:
        stop = getattr(session, "stop", None)
        if callable(stop):
            result = stop()
            if inspect.isawaitable(result):
                await result


class JobPilot:
    """High-level JobPilot workflow using the existing Browser Use/Harness stack."""

    def __init__(self, *, model: str = "gemini-3.6-flash", max_steps: int = 80) -> None:
        if not model.strip():
            raise ValueError("model must not be empty")
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.model = model
        self.max_steps = max_steps

    def prepare_plan(self, job: JobDescription, resume_text: str, profile: ContactProfile, *, answers: dict[str, str] | None = None) -> ApplicationPlan:
        """Prepare deterministic ATS score and safe document variants."""
        match = score_job_match(job.description, resume_text)
        tailored = tailor_resume_text(resume_text, match.missing_keywords)
        cover_letter = build_cover_letter(job, profile, resume_text=resume_text)
        plan = ApplicationPlan(job=job, profile=profile, match=match, tailored_resume_text=tailored, cover_letter=cover_letter, answers=dict(answers or {}), auto_submit=False)
        plan.validate()
        return plan

    async def prepare_plan_async(
        self, job: JobDescription, resume_text: str, profile: ContactProfile, *, answers: dict[str, str] | None = None, use_llm: bool = True
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
        plan = ApplicationPlan(job=job, profile=profile, match=match, tailored_resume_text=tailored, cover_letter=cover_letter, answers=dict(answers or {}), auto_submit=False)
        plan.validate()
        return plan

    @staticmethod
    def _validate_resume_path(resume_path: str) -> None:
        path = Path(resume_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"resume not found: {path}")

    async def apply_to_open_page(self, plan: ApplicationPlan, *, resume_path: str) -> Any:
        """Fill the already-open application page and stop before submission."""
        self._validate_resume_path(resume_path)
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
        _validate_web_url(plan.job.url, field_name="job application URL")
        self._validate_resume_path(resume_path)
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
