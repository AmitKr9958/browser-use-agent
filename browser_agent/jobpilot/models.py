"""Typed data models for the JobPilot application workflow."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ContactProfile:
    """User-provided application data. Empty values are intentionally preserved."""

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    portfolio: str = ""
    work_authorization: str = ""
    sponsorship: str = ""


@dataclass(frozen=True, slots=True)
class JobDescription:
    """Normalized job information used by ATS and document generation."""

    title: str
    company: str
    description: str
    url: str = ""
    location: str = ""


@dataclass(frozen=True, slots=True)
class MatchScore:
    """Explainable keyword-based match score."""

    score: float
    matched_keywords: tuple[str, ...] = ()
    missing_keywords: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ApplicationPlan:
    """Artifacts and browser instructions prepared before any sensitive action."""

    job: JobDescription
    profile: ContactProfile
    match: MatchScore
    tailored_resume_text: str
    cover_letter: str
    answers: dict[str, str] = field(default_factory=dict)
    auto_submit: bool = False

    def validate(self) -> None:
        if self.auto_submit:
            raise ValueError("JobPilot never permits automatic final application submission")
        if not self.job.description.strip():
            raise ValueError("job description must not be empty")
        if not self.tailored_resume_text.strip():
            raise ValueError("tailored resume must not be empty")
