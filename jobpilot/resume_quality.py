"""Deterministic quality checks for generated ATS resume text."""

from __future__ import annotations

from dataclasses import dataclass

from .models import ResumeProfile


@dataclass(frozen=True, slots=True)
class ResumeQuality:
    valid: bool
    errors: tuple[str, ...]


def validate_ats_resume(text: str, profile: ResumeProfile) -> ResumeQuality:
    """Check basic ATS-safe structure and preservation of core contact facts."""
    errors: list[str] = []
    normalized = text.casefold()
    if not text.strip():
        errors.append("resume is empty")
    if profile.name.casefold() not in normalized:
        errors.append("candidate name is missing")
    if profile.email.casefold() not in normalized:
        errors.append("candidate email is missing")
    if "|" in text:
        errors.append("markdown table syntax is not ATS-safe")
    if "![" in text or "<img" in normalized:
        errors.append("images are not ATS-safe")
    if any(marker in text for marker in ("<!--", "-->")):
        errors.append("HTML comments are not allowed")
    return ResumeQuality(valid=not errors, errors=tuple(errors))
