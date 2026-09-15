"""Resume and contact-profile loading helpers for JobPilot."""

from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from .models import ContactProfile

_EMAIL = re.compile(r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")


def _append_nonempty(chunks: list[str], value: str) -> None:
    value = value.strip()
    if value and value not in chunks:
        chunks.append(value)


def extract_resume_text(path: str | Path) -> str:
    """Extract resume text with layout-independent evidence from common formats."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"resume not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".pdf":
        chunks: list[str] = []
        reader = PdfReader(str(source))
        for page in reader.pages:
            _append_nonempty(chunks, page.extract_text() or "")
        return "\n".join(chunks).strip()
    if suffix == ".docx":
        document = Document(str(source))
        chunks = []
        for section in document.sections:
            for paragraph in section.header.paragraphs:
                _append_nonempty(chunks, paragraph.text)
        for paragraph in document.paragraphs:
            _append_nonempty(chunks, paragraph.text)
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    _append_nonempty(chunks, " | ".join(cells))
        for section in document.sections:
            for paragraph in section.footer.paragraphs:
                _append_nonempty(chunks, paragraph.text)
        return "\n".join(chunks).strip()
    if suffix in {".txt", ".md"}:
        return source.read_text(encoding="utf-8").strip()
    raise ValueError("unsupported resume format; use PDF, DOCX, TXT, or MD")


def load_contact_profile(path: str | Path) -> ContactProfile:
    """Load a JSON contact profile and reject unknown fields."""
    source = Path(path).expanduser()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("contact profile must be a JSON object")
    allowed = {item.name for item in fields(ContactProfile)}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"unknown contact fields: {', '.join(sorted(unknown))}")
    values = {key: str(value).strip() for key, value in data.items() if value is not None}
    return ContactProfile(**values)


def infer_contact_profile(text: str) -> ContactProfile:
    """Extract only low-risk contact values; never infer identity or credentials."""
    if not text.strip():
        return ContactProfile()
    email = _EMAIL.search(text)
    phone = _PHONE.search(text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines and not _EMAIL.fullmatch(lines[0]) else ""
    return ContactProfile(name=name, email=email.group(0) if email else "", phone=phone.group(0) if phone else "")
