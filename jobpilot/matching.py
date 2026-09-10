"""Lightweight deterministic matching used before and after LLM tailoring."""

from __future__ import annotations

import re

from .models import Job, ResumeProfile


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,30}", text.casefold()) if len(token) > 2}


def match_keywords(job: Job, profile: ResumeProfile) -> tuple[list[str], list[str]]:
    """Return supported job tokens and visible gaps; this is a signal, not an ATS score."""
    job_tokens = _tokens(f"{job.title} {job.description}")
    profile_text = " ".join(
        [profile.headline or "", profile.summary or "", *profile.skills, str(profile.experience), str(profile.education)]
    )
    candidate_tokens = _tokens(profile_text)
    matched = sorted(job_tokens & candidate_tokens)
    missing = sorted(job_tokens - candidate_tokens)
    return matched, missing
