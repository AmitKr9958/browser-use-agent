"""LLM-powered application material generation."""

from __future__ import annotations

from typing import Any

from browser_use.llm.messages import UserMessage

from .field_policy import is_safe_autofill_label
from .models import Job, ResumeProfile
from .prompts import application_question_prompt, cover_letter_prompt, resume_prompt


async def _invoke_text(llm: Any, prompt: str) -> str:
    response = await llm.ainvoke([UserMessage(content=prompt)])
    text = getattr(response, "content", response)
    if isinstance(text, list):
        text = "\n".join(str(item) for item in text)
    result = str(text).strip()
    if not result:
        raise RuntimeError("LLM returned empty generation output")
    return result


async def generate_resume(llm: Any, job: Job, profile: ResumeProfile, current_resume: str) -> str:
    """Tailor an existing resume without inventing candidate facts."""
    if not current_resume.strip():
        raise ValueError("current_resume must not be empty")
    return await _invoke_text(llm, resume_prompt(job, profile, current_resume))


async def generate_cover_letter(llm: Any, job: Job, profile: ResumeProfile, resume_markdown: str) -> str:
    """Generate a truthful cover letter from the tailored resume and candidate facts."""
    return await _invoke_text(llm, cover_letter_prompt(job, profile, resume_markdown))


async def answer_application_question(
    llm: Any,
    job: Job,
    profile: ResumeProfile,
    question: str,
) -> str:
    """Answer only safe questions whose answer is supported by candidate facts."""
    if not question.strip():
        raise ValueError("question must not be empty")
    if not is_safe_autofill_label(question):
        return "NEEDS_REVIEW"
    return await _invoke_text(llm, application_question_prompt(job, profile, question))
