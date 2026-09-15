"""Deterministic audit and reconciliation primitives for JobPilot.

The browser agent is treated as an untrusted executor: natural-language claims are
not accepted as proof. Structured field observations are reconciled against the
plan, and only explicitly user-attributed changes can become learned corrections.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any


_VALID_SOURCES = {"agent", "resume", "user", "existing_page", "unknown"}
_VALID_STATUSES = {"filled", "verified", "skipped", "conflict", "manual", "unmapped"}


@dataclass(frozen=True, slots=True)
class FieldAudit:
    """One field-level observation from the live application page."""

    label: str
    field_type: str = ""
    planned_value: str = ""
    observed_value: str = ""
    source: str = "unknown"
    status: str = "manual"
    verified: bool = False
    reason: str = ""
    step: str = ""

    def validate(self) -> None:
        if not self.label.strip():
            raise ValueError("field audit label must not be empty")
        if self.source not in _VALID_SOURCES:
            raise ValueError(f"unsupported field audit source: {self.source}")
        if self.status not in _VALID_STATUSES:
            raise ValueError(f"unsupported field audit status: {self.status}")


@dataclass(frozen=True, slots=True)
class CorrectionCandidate:
    """A proposed learning event; it is valid only when explicitly user-attributed."""

    field: str
    before_value: str
    after_value: str
    source: str = "user"
    explicit: bool = False
    reason: str = ""
    step: str = ""

    def validate(self) -> None:
        if not self.field.strip() or not self.after_value.strip():
            raise ValueError("correction field and after_value are required")
        if self.source != "user" or not self.explicit:
            raise ValueError("only explicit user corrections may enter persistent memory")


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def parse_structured_result(raw: str) -> dict[str, Any] | None:
    """Extract a JSON object from an agent result, rejecting malformed structures."""
    text = raw.strip()
    if not text:
        return None
    if "```" in text:
        text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def parse_field_audits(data: dict[str, Any]) -> tuple[FieldAudit, ...]:
    """Validate the field audit list returned by the browser agent."""
    raw_fields = data.get("fields", [])
    if not isinstance(raw_fields, list):
        return ()
    result: list[FieldAudit] = []
    for raw in raw_fields:
        if not isinstance(raw, dict):
            continue
        item = FieldAudit(
            label=_text(raw.get("label")),
            field_type=_text(raw.get("type", raw.get("field_type"))),
            planned_value=_text(raw.get("planned_value")),
            observed_value=_text(raw.get("observed_value")),
            source=_text(raw.get("source")) or "unknown",
            status=_text(raw.get("status")) or "manual",
            verified=bool(raw.get("verified", False)),
            reason=_text(raw.get("reason")),
            step=_text(raw.get("step")),
        )
        try:
            item.validate()
        except ValueError:
            continue
        result.append(item)
    return tuple(result)


def parse_corrections(data: dict[str, Any]) -> tuple[CorrectionCandidate, ...]:
    """Accept only corrections carrying an explicit user source and flag."""
    raw_items = data.get("corrections", [])
    if not isinstance(raw_items, list):
        return ()
    result: list[CorrectionCandidate] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            continue
        candidate = CorrectionCandidate(
            field=_text(raw.get("field")),
            before_value=_text(raw.get("before_value")),
            after_value=_text(raw.get("after_value")),
            source=_text(raw.get("source")) or "unknown",
            explicit=bool(raw.get("explicit", False)),
            reason=_text(raw.get("reason")),
            step=_text(raw.get("step")),
        )
        try:
            candidate.validate()
        except ValueError:
            continue
        result.append(candidate)
    return tuple(result)


def reconcile_fields(fields: tuple[FieldAudit, ...]) -> tuple[FieldAudit, ...]:
    """Upgrade an observation to verified only when the live value matches the plan."""
    result: list[FieldAudit] = []
    for field in fields:
        if field.planned_value and field.observed_value == field.planned_value and field.status in {"filled", "verified"}:
            result.append(FieldAudit(**{**asdict(field), "status": "verified", "verified": True}))
        else:
            result.append(field)
    return tuple(result)


def audit_metadata(data: dict[str, Any], fields: tuple[FieldAudit, ...]) -> dict[str, Any]:
    """Build stable metadata suitable for ApplicationReport and JSON output."""
    reconciled = reconcile_fields(fields)
    return {
        "verification_signal": any(field.verified for field in reconciled),
        "final_submission_control_present": bool(data.get("final_submission_control_present", False)),
        "final_page": _text(data.get("final_page")),
        "fields": [asdict(field) for field in reconciled],
        "corrections": [asdict(item) for item in parse_corrections(data)],
    }
