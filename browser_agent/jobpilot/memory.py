"""Persistent, provenance-aware application memory for JobPilot.

Memory is deliberately small and evidence-first: resume facts are a fallback,
while explicit user corrections may override them. Secrets and high-risk
identity data are never persisted by this module.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ContactProfile

_SENSITIVE = re.compile(
    r"(?:password|passcode|otp|one[- ]?time|mfa|2fa|captcha|aadhaar|pan\b|uan\b|passport|"
    r"driver.?s? license|driving license|government.?id|social security|ssn\b|tax id|"
    r"national id|identity (?:number|document)|bank|routing|credit card|debit card)",
    re.I,
)

@dataclass(frozen=True, slots=True)
class LearnedAnswer:
    question: str
    answer: str
    source: str = "user"
    updated_at: str = ""
    confidence: str = "explicit"


def default_memory_path() -> Path:
    """Return a private, user-scoped memory path outside the source repository."""
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return root / "JobPilot" / "memory.json"


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "profile": {}, "answers": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("unsupported JobPilot memory format")
    data.setdefault("profile", {})
    data.setdefault("answers", {})
    return data


def load_memory(path: str | Path) -> dict[str, Any]:
    """Load memory without mutating it."""
    return _read(Path(path).expanduser())


def merge_profile(base: ContactProfile, path: str | Path | None) -> ContactProfile:
    """Overlay explicit learned profile values onto resume-derived values."""
    if not path:
        return base
    data = _read(Path(path).expanduser())
    values = asdict(base)
    for field, value in data.get("profile", {}).items():
        if field in values and isinstance(value, str) and value.strip() and not _SENSITIVE.search(field):
            values[field] = value.strip()
    return ContactProfile(**values)


def learned_answers(path: str | Path | None) -> dict[str, str]:
    if not path:
        return {}
    data = _read(Path(path).expanduser())
    return {
        str(key): str(item.get("answer", "")).strip()
        for key, item in data.get("answers", {}).items()
        if isinstance(item, dict) and str(item.get("answer", "")).strip()
    }


def lookup_answer(path: str | Path | None, question: str) -> str | None:
    """Find a learned answer using normalized semantic-key equality."""
    wanted = _key(question)
    if not wanted or not path:
        return None
    answers = learned_answers(path)
    if wanted in answers:
        return answers[wanted]
    for key, value in answers.items():
        if _key(key) == wanted:
            return value
    return None


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".jobpilot-memory-", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def remember_user_value(path: str | Path, field: str, value: str) -> bool:
    """Persist an explicit user correction; return False for unsafe/sensitive data."""
    field = field.strip()
    value = value.strip()
    if not field or not value or _SENSITIVE.search(field):
        return False
    destination = Path(path).expanduser()
    data = _read(destination)
    profile_fields = {f.name for f in ContactProfile.__dataclass_fields__.values()}
    now = datetime.now(timezone.utc).isoformat()
    if field in profile_fields:
        data["profile"][field] = value
    else:
        data["answers"][_key(field)] = asdict(LearnedAnswer(field, value, "user", now, "explicit"))
    _write(destination, data)
    return True


def remember_correction(
    path: str | Path,
    *,
    field: str,
    before_value: str,
    after_value: str,
    reason: str = "explicit user correction",
) -> bool:
    """Persist a browser correction only after explicit user attribution."""
    if not field.strip() or not after_value.strip() or _SENSITIVE.search(field):
        return False
    if before_value.strip() == after_value.strip():
        return False
    return remember_user_value(path, field, after_value)
