"""Fast, explainable ATS matching without requiring an LLM call."""

from __future__ import annotations

import re
from collections import Counter

_STOP_WORDS = {
    "about", "after", "also", "been", "being", "between", "could", "from", "have", "into",
    "more", "other", "over", "should", "their", "there", "these", "they", "this", "those",
    "through", "using", "very", "were", "what", "when", "where", "which", "while", "with",
    "would", "your", "you", "role", "work", "team", "job", "company", "years", "year",
}


def _terms(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#./-]{2,}", text.lower())
    return [word for word in words if word not in _STOP_WORDS]


def score_job_match(job_description: str, resume_text: str, *, max_keywords: int = 40):
    """Return a deterministic, explainable match score based on repeated JD terms."""
    if not job_description.strip():
        raise ValueError("job_description must not be empty")
    if not resume_text.strip():
        raise ValueError("resume_text must not be empty")
    if max_keywords < 1:
        raise ValueError("max_keywords must be at least 1")

    counts = Counter(_terms(job_description))
    keywords = [word for word, _ in counts.most_common(max_keywords)]
    resume_terms = set(_terms(resume_text))
    matched = tuple(word for word in keywords if word in resume_terms)
    missing = tuple(word for word in keywords if word not in resume_terms)
    score = round((len(matched) / len(keywords)) * 100, 1) if keywords else 0.0

    from .models import MatchScore

    return MatchScore(score=score, matched_keywords=matched, missing_keywords=missing)
