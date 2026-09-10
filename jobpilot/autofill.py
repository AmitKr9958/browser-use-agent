"""Fast, conservative application-form field mapping."""

from __future__ import annotations

import re
from typing import Iterable

from .field_policy import is_safe_autofill_label
from .models import ResumeProfile

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "full name", "candidate name", "applicant name"),
    "email": ("email", "email address", "e-mail"),
    "phone": ("phone", "phone number", "mobile", "mobile number", "telephone"),
    "location": ("city", "location", "current location"),
    "linkedin": ("linkedin", "linkedin url", "linkedin profile"),
    "github": ("github", "github url", "github profile"),
}

_EXCLUSIONS: dict[str, tuple[str, ...]] = {
    "name": ("company", "school", "university", "employer", "job title"),
    "location": ("address", "street", "postal", "zip", "state", "country"),
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def build_field_values(profile: ResumeProfile) -> dict[str, str]:
    """Build deterministic values backed only by explicit candidate data."""
    values = {"name": profile.name, "email": profile.email}
    if profile.phone:
        values["phone"] = profile.phone
    if profile.location:
        values["location"] = profile.location
    for key in ("linkedin", "github"):
        if profile.links.get(key):
            values[key] = profile.links[key]
    return values


def classify_field(*labels: str) -> str | None:
    """Map form attributes to a profile field with conservative matching."""
    normalized = [_normalize(label) for label in labels if label.strip()]
    for field, aliases in _FIELD_ALIASES.items():
        if any(exclusion in value for value in normalized for exclusion in _EXCLUSIONS.get(field, ())):
            continue
        for value in normalized:
            if not value:
                continue
            for alias in aliases:
                normalized_alias = _normalize(alias)
                if value == normalized_alias or normalized_alias in value:
                    return field
    return None


def map_form_fields(labels: Iterable[str], profile: ResumeProfile) -> dict[str, str]:
    """Map safe, uniquely understood labels to profile values."""
    values = build_field_values(profile)
    result: dict[str, str] = {}
    for label in labels:
        if not is_safe_autofill_label(label):
            continue
        field = classify_field(label)
        if field and field in values:
            result[label] = values[field]
    return result
