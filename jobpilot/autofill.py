"""Fast, conservative application-form field mapping.

This module intentionally handles only fields whose values are explicitly present in
ResumeProfile. Unknown or sensitive questions are left for the AI/manual review layer.
"""

from __future__ import annotations

import re
from typing import Iterable

from .models import ResumeProfile

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "full name", "candidate name", "applicant name"),
    "email": ("email", "email address", "e-mail"),
    "phone": ("phone", "phone number", "mobile", "mobile number", "telephone"),
    "location": ("city", "location", "current location", "address"),
    "linkedin": ("linkedin", "linkedin url", "linkedin profile"),
    "github": ("github", "github url", "github profile"),
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def build_field_values(profile: ResumeProfile) -> dict[str, str]:
    """Build the small set of deterministic values safe to fill automatically."""
    values = {
        "name": profile.name,
        "email": profile.email,
    }
    if profile.phone:
        values["phone"] = profile.phone
    if profile.location:
        values["location"] = profile.location
    for key in ("linkedin", "github"):
        if profile.links.get(key):
            values[key] = profile.links[key]
    return values


def classify_field(*labels: str) -> str | None:
    """Map visible/attribute labels to a deterministic profile field."""
    normalized = {_normalize(label) for label in labels if label.strip()}
    for field, aliases in _FIELD_ALIASES.items():
        if any(_normalize(alias) in value or value in _normalize(alias) for value in normalized for alias in aliases):
            return field
    return None


def map_form_fields(labels: Iterable[str], profile: ResumeProfile) -> dict[str, str]:
    """Map field labels to values; duplicate/unknown labels are skipped."""
    values = build_field_values(profile)
    result: dict[str, str] = {}
    for label in labels:
        field = classify_field(label)
        if field and field in values:
            result[label] = values[field]
    return result
