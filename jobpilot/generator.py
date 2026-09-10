"""LLM-powered application material generation."""

from __future__ import annotations

from typing import Any

from browser_use.llm.messages import UserMessage

from .models import Job, ResumeProfile
from .prompts import cover_letter_prompt, resume_prompt


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
