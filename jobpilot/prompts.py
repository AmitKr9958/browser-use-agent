"""Prompt builders for resume and cover-letter generation."""

from __future__ import annotations

from jobpilot.models import Job, ResumeProfile


def resume_prompt(job: Job, profile: ResumeProfile, current_resume: str) -> str:
    return f"""Create an ATS-friendly resume tailored to this job.

JOB
Title: {job.title}
Company: {job.company}
Description:
{job.description}

CANDIDATE FACTS
{profile.model_dump_json(indent=2)}

CURRENT RESUME
{current_resume}

Rules:
- Preserve truthful candidate facts; never invent employers, dates, degrees, skills, metrics, certifications, or tools.
- Reorder and rewrite existing evidence to emphasize relevant requirements.
- Use plain ATS-friendly text and standard section headings.
- Include keywords only when supported by the candidate facts or current resume.
- Do not add a photo, graphics, tables, columns, or decorative formatting.
Return only the revised resume in Markdown.
"""


def cover_letter_prompt(job: Job, profile: ResumeProfile, resume_markdown: str) -> str:
    return f"""Write a concise tailored cover letter for this application.

JOB
{job.model_dump_json(indent=2)}

CANDIDATE
{profile.model_dump_json(indent=2)}

TAILORED RESUME
{resume_markdown}

Rules:
- Use only truthful information present in the candidate data or resume.
- Do not invent achievements, relationships, projects, salary expectations, or reasons for leaving.
- Focus on the strongest evidence relevant to this role.
- Keep it professional and concise.
Return only the cover letter text.
"""
