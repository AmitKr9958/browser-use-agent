"""Deterministic resume evidence extraction for safe JobPilot generation."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SECTION_RE = re.compile(
    r"^(?:#+\s*)?(?P<name>summary|professional summary|profile|skills?|technical skills|core skills|experience|work experience|professional experience|employment|education|certifications?|licenses?|projects?|achievements?)\s*:?[\s]*$",
    re.I,
)
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


@dataclass(frozen=True)
class EvidenceItem:
    """A source-backed resume fragment that may be cited by generation prompts."""

    section: str
    text: str


def extract_resume_evidence(resume_text: str, *, max_items: int = 120) -> tuple[EvidenceItem, ...]:
    """Extract compact, source-backed resume evidence without semantic guessing."""
    if not resume_text.strip():
        raise ValueError("resume_text must not be empty")
    if max_items <= 0:
        raise ValueError("max_items must be positive")

    current = "General"
    items: list[EvidenceItem] = []
    for raw in resume_text.splitlines():
        line = " ".join(raw.strip().split())
        if not line:
            continue
        match = _SECTION_RE.match(line)
        if match:
            current = match.group("name").strip().title()
            continue
        # Keep original facts, while removing only presentation-only bullet markers.
        text = _BULLET_RE.sub("", line).strip()
        if text:
            items.append(EvidenceItem(section=current, text=text))
            if len(items) >= max_items:
                break
    return tuple(items)


def format_resume_evidence(resume_text: str, *, max_items: int = 120) -> str:
    """Format deterministic evidence for an LLM prompt; no new facts are introduced."""
    evidence = extract_resume_evidence(resume_text, max_items=max_items)
    if not evidence:
        return "(No structured evidence extracted.)"
    return "\n".join(f"[{item.section}] {item.text}" for item in evidence)
