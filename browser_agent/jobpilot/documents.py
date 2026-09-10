"""Deterministic resume tailoring and cover-letter generation."""

from __future__ import annotations

from .models import ContactProfile, JobDescription


def tailor_resume_text(resume_text: str, missing_keywords: tuple[str, ...], *, max_additions: int = 15) -> str:
    """Create an ATS-oriented text variant without inventing experience.

    Missing terms are presented as a review list rather than fabricated resume claims.
    This keeps the MVP truthful while still making keyword gaps immediately actionable.
    """
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


def build_cover_letter(job: JobDescription, profile: ContactProfile, *, resume_text: str = "") -> str:
    """Build a concise cover letter from supplied facts only."""
    name = profile.name or "Hiring Team"
    greeting = "Dear Hiring Team," if not profile.name else "Dear Hiring Team,"
    evidence = "I would welcome the opportunity to discuss how my experience can contribute to this role."
    if resume_text.strip():
        evidence = "My background aligns with the role's requirements, and I would welcome the opportunity to discuss the strongest relevant examples."
    return (
        f"{greeting}\n\n"
        f"I am interested in the {job.title} opportunity at {job.company}. "
        f"{evidence}\n\n"
        "I am particularly interested in the scope described in the job posting and the opportunity to contribute to the team. "
        "I have attached my resume for consideration and would be happy to provide additional information.\n\n"
        "Thank you for your time and consideration.\n\n"
        f"Regards,\n{name}"
    )
