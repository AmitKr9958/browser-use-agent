"""Resume tailoring and cover-letter generation for JobPilot."""

from __future__ import annotations

from browser_use import ChatGoogle
from browser_use.llm.messages import UserMessage

from .models import ContactProfile, JobDescription


def tailor_resume_text(resume_text: str, missing_keywords: tuple[str, ...], *, max_additions: int = 15) -> str:
    """Create a deterministic ATS review draft without inventing experience."""
    if not resume_text.strip():
        raise ValueError("resume_text must not be empty")
    additions = tuple(dict.fromkeys(word.strip() for word in missing_keywords if word.strip()))[:max_additions]
    if not additions:
        return resume_text.strip()
    review = "\n".join(f"- {word}" for word in additions)
    return (
        f"{resume_text.strip()}\n\n"
        "[JOBPILOT REVIEW — add only if accurate]\n"
        "Relevant keywords from the job description not found in the current resume:\n"
        f"{review}"
    )


async def tailor_resume_with_llm(
    resume_text: str,
    job_description: str,
    *,
    model: str = "gemini-3-flash-preview",
) -> str:
    """Generate an ATS-focused resume draft while explicitly prohibiting invented facts.

    The result is a draft for user verification; the browser workflow continues to use the
    supplied resume file unless the user explicitly replaces it with the reviewed draft.
    """
    if not resume_text.strip() or not job_description.strip():
        raise ValueError("resume_text and job_description must not be empty")
    prompt = f"""
Rewrite the resume below for the target job description.

STRICT RULES:
- Use only facts, employers, titles, dates, education, certifications, skills, and achievements already present in the source resume.
- Do not invent metrics, responsibilities, technologies, employers, credentials, locations, or years of experience.
- You may reorder sections, tighten wording, remove repetition, and emphasize experience that is already present.
- If a job keyword is not supported by the source resume, do not add it as a claimed skill.
- Keep the output ATS-friendly: plain text headings, concise bullets, no tables, no icons, no graphics.
- Return only the revised resume text, with no explanation.

TARGET JOB:
{job_description}

SOURCE RESUME:
{resume_text}
""".strip()
    llm = ChatGoogle(model=model)
    response = await llm.ainvoke([UserMessage(content=prompt)])
    output = str(response.completion).strip()
    if not output:
        raise RuntimeError("resume tailoring model returned empty output")
    return output


def build_cover_letter(job: JobDescription, profile: ContactProfile, *, resume_text: str = "") -> str:
    """Build a concise cover letter from supplied facts only."""
    name = profile.name or "Applicant"
    evidence = "I would welcome the opportunity to discuss how my experience can contribute to this role."
    if resume_text.strip():
        evidence = "My background includes experience relevant to the requirements described in the posting, and I would welcome the opportunity to discuss the strongest examples."
    return (
        "Dear Hiring Team,\n\n"
        f"I am interested in the {job.title} opportunity at {job.company}. "
        f"{evidence}\n\n"
        "I am particularly interested in the scope described in the job posting and the opportunity to contribute to the team. "
        "Please find my resume attached for consideration.\n\n"
        "Thank you for your time and consideration.\n\n"
        f"Regards,\n{name}"
    )


async def build_cover_letter_with_llm(
    job: JobDescription,
    profile: ContactProfile,
    resume_text: str,
    *,
    model: str = "gemini-3-flash-preview",
) -> str:
    """Generate a targeted cover-letter draft using only supplied resume/profile facts."""
    if not resume_text.strip():
        return build_cover_letter(job, profile)
    prompt = f"""
Write a concise, professional cover letter for this job.

STRICT RULES:
- Use only facts explicitly present in the resume or contact profile below.
- Do not invent achievements, employers, technologies, years, certifications, metrics, or responsibilities.
- Do not mention skills that are not supported by the resume.
- Keep it to 250 words or fewer.
- Return only the letter text.

JOB:
Title: {job.title}
Company: {job.company}
Description:
{job.description}

CONTACT PROFILE:
Name: {profile.name}

RESUME:
{resume_text}
""".strip()
    llm = ChatGoogle(model=model)
    response = await llm.ainvoke([UserMessage(content=prompt)])
    output = str(response.completion).strip()
    if not output:
        raise RuntimeError("cover-letter model returned empty output")
    return output
