"""Deterministic, evidence-first handling for common career-site questions."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import ContactProfile


@dataclass(frozen=True, slots=True)
class QuestionDecision:
    """A safe answer decision for a common application question."""

    answer: str | None
    reason: str
    confidence: str


_YES_PATTERNS = (
    re.compile(r"\bdo you (?:have|possess)\b.*\b(?:skill|experience|knowledge)\b", re.I),
    re.compile(r"\bare you (?:proficient|experienced|skilled)\b", re.I),
)
_AUTH_PATTERNS = (
    re.compile(r"authorized to work", re.I),
    re.compile(r"legally (?:authorized|eligible) to work", re.I),
    re.compile(r"work authorization", re.I),
)
_SPONSOR_PATTERNS = (
    re.compile(r"require.*sponsor", re.I),
    re.compile(r"need.*sponsorship", re.I),
    re.compile(r"visa sponsorship", re.I),
)
_CONTACT_PATTERNS = {
    "email": re.compile(r"\bemail\b", re.I),
    "phone": re.compile(r"\b(?:phone|mobile|telephone)\b", re.I),
    "linkedin": re.compile(r"\blinkedin\b", re.I),
    "portfolio": re.compile(r"\b(?:portfolio|website)\b", re.I),
}


def _matches_any(question: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(question) for pattern in patterns)


def _skill_from_question(question: str, resume_text: str) -> str | None:
    """Return yes only when a named skill is explicitly present in the resume."""
    candidates = re.findall(r"[A-Za-z][A-Za-z0-9+#./ -]{1,40}", question)
    resume_lower = resume_text.casefold()
    for candidate in candidates:
        candidate = " ".join(candidate.split()).strip(" ?.,:;()[]")
        if len(candidate) < 3 or candidate.casefold() in {"the", "you", "have", "experience", "skill", "skills"}:
            continue
        if candidate.casefold() in resume_lower:
            return candidate
    return None


def answer_application_question(question: str, *, profile: ContactProfile, resume_text: str) -> QuestionDecision:
    """Answer only questions whose answers are directly supported by supplied evidence.

    Unknown personal, legal, demographic, compensation, availability, or identity
    questions deliberately return ``None`` rather than inventing an answer.
    """
    q = " ".join(question.split()).strip()
    if not q:
        return QuestionDecision(None, "empty question", "none")

    for key, pattern in _CONTACT_PATTERNS.items():
        if pattern.search(q):
            value = getattr(profile, key)
            if value:
                return QuestionDecision(value, f"explicit profile {key}", "high")

    if _matches_any(q, _AUTH_PATTERNS) and profile.work_authorization:
        return QuestionDecision(profile.work_authorization, "explicit profile work authorization", "high")

    if _matches_any(q, _SPONSOR_PATTERNS) and profile.sponsorship:
        return QuestionDecision(profile.sponsorship, "explicit profile sponsorship preference", "high")

    if _matches_any(q, _YES_PATTERNS):
        skill = _skill_from_question(q, resume_text)
        if skill:
            return QuestionDecision("Yes", f"resume explicitly contains {skill}", "high")

    return QuestionDecision(None, "answer not explicitly supported by profile or resume", "none")


def build_questionnaire_policy() -> str:
    """Return the browser-agent policy for common application questions."""
    return """
QUESTIONNAIRE POLICY
- Automatically answer ordinary application questions when the answer is explicitly supported by the supplied profile or resume.
- For skill/experience questions, answer Yes only when the named skill or experience is explicitly present in the resume; otherwise leave unanswered.
- Use supplied work-authorization and sponsorship values only when those exact values are present in the profile.
- Use supplied contact values for matching contact fields.
- Never guess or infer salary, notice period, availability/start date, relocation willingness, visa status, legal attestations, demographic/EEO information, disability/veteran status, criminal history, age/date of birth, identity numbers, passwords, OTPs, or consent statements.
- Never invent a yes/no answer merely because it seems typical for the candidate.
- If a mandatory question cannot be answered from supplied evidence, stop and report the exact question for manual review.
- Never click a final submission control.
""".strip()
