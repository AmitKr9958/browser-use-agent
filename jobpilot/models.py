"""Typed domain models for job targeting and application preparation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Job(BaseModel):
    """A normalized job record independent of a specific career-site database."""

    model_config = ConfigDict(extra="allow")

    title: str
    company: str
    url: str
    description: str = ""
    location: str | None = None
    employment_type: str | None = None
    application_url: str | None = None
    ats: str | None = None


class ResumeProfile(BaseModel):
    """Candidate facts used for truthful resume and application generation."""

    model_config = ConfigDict(extra="allow")

    name: str
    email: str
    phone: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[dict[str, object]] = Field(default_factory=list)
    education: list[dict[str, object]] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


class JobApplicationDraft(BaseModel):
    """Generated application material awaiting human review and submission."""

    job: Job
    resume_markdown: str
    cover_letter: str
    matched_keywords: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    autofill_fields: dict[str, str] = Field(default_factory=dict)
    ready_for_review: bool = False


class ApplicationReview(BaseModel):
    """Auditable result of preparing and safely autofilling an application."""

    draft: JobApplicationDraft
    ats: str
    filled_fields: list[dict[str, str | int]] = Field(default_factory=list)
    skipped_fields: list[dict[str, str | int]] = Field(default_factory=list)
    unknown_fields: list[dict[str, str | int]] = Field(default_factory=list)
    resume_path: str | None = None
    cover_letter_path: str | None = None
    ready_for_review: bool = True
    submitted: bool = False
