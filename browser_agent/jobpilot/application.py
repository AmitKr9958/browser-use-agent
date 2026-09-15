"""Structured results for controlled job-application runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .audit import audit_metadata, parse_field_audits, parse_structured_result


_SUBMISSION_MARKERS = (
    "application submitted",
    "successfully submitted",
    "submission successful",
    "submitted successfully",
    "application has been submitted",
)
_BLOCKER_PATTERNS = (
    re.compile(r"\bcaptcha\b", re.IGNORECASE),
    re.compile(r"\bmfa\b", re.IGNORECASE),
    re.compile(r"\botp\b", re.IGNORECASE),
    re.compile(r"\bverification code\b", re.IGNORECASE),
    re.compile(r"\blogin required\b", re.IGNORECASE),
    re.compile(r"\bpayment required\b", re.IGNORECASE),
    re.compile(r"\bidentity verification\b", re.IGNORECASE),
)
_EXPLICIT_VERIFICATION_MARKERS = (
    "field value verified",
    "fields verified",
    "filled and verified",
    "value matches",
    "filename visible",
    "file attached",
    "upload verified",
    "attachment verified",
    "control reports the file as attached",
    "visible and verified",
)
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_SECRET_RE = re.compile(
    r"\b(password|passwd|otp|one[- ]time code|verification code)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_MAX_RAW_RESULT = 8_000


def _redact_secret(match: re.Match[str]) -> str:
    key = match.group(1)
    return f"{key}: [REDACTED]"


def _sanitize_result(text: str) -> str:
    """Remove common personal/secret values before a result is persisted or printed."""
    sanitized = _SECRET_RE.sub(_redact_secret, text)
    sanitized = _EMAIL_RE.sub("[EMAIL REDACTED]", sanitized)
    sanitized = _PHONE_RE.sub("[PHONE REDACTED]", sanitized)
    return sanitized[:_MAX_RAW_RESULT]


@dataclass(frozen=True, slots=True)
class ApplicationReport:
    """Machine-readable summary of an autofill attempt."""

    status: str
    target_url: str
    filled_fields: tuple[str, ...] = ()
    skipped_fields: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    submitted: bool = False
    raw_result: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.status not in {"completed", "blocked", "no_form", "failed"}:
            raise ValueError(f"invalid application status: {self.status}")
        if self.submitted:
            raise ValueError("JobPilot reports must never mark an application as submitted")
        if not self.target_url.strip():
            raise ValueError("application report target_url must not be empty")
        if self.status == "completed" and self.metadata.get("verification_signal") is not True:
            raise ValueError("completed application reports require explicit verification")
        if self.status == "blocked" and not self.blockers:
            raise ValueError("blocked application reports require a blocker reason")


def build_application_report(
    *,
    status: str,
    target_url: str,
    filled_fields: list[str] | tuple[str, ...] = (),
    skipped_fields: list[str] | tuple[str, ...] = (),
    blockers: list[str] | tuple[str, ...] = (),
    raw_result: str = "",
    metadata: dict[str, Any] | None = None,
) -> ApplicationReport:
    report = ApplicationReport(
        status=status,
        target_url=target_url,
        filled_fields=tuple(filled_fields),
        skipped_fields=tuple(skipped_fields),
        blockers=tuple(blockers),
        submitted=False,
        raw_result=_sanitize_result(raw_result),
        metadata=dict(metadata or {}),
    )
    report.validate()
    return report


def build_application_report_from_result(*, target_url: str, raw_result: str) -> ApplicationReport:
    """Convert an agent result into a conservative, privacy-aware report."""
    text = raw_result.strip()
    lowered = text.lower()

    if any(marker in lowered for marker in _SUBMISSION_MARKERS):
        return build_application_report(
            status="failed",
            target_url=target_url,
            blockers=("agent result indicates a submission may have occurred; manual review required",),
            raw_result=text,
            metadata={"submission_signal": True, "verification_signal": False},
        )

    blockers = tuple(
        pattern.pattern.removeprefix(r"\b").removesuffix(r"\b")
        for pattern in _BLOCKER_PATTERNS
        if pattern.search(text)
    )
    if blockers:
        return build_application_report(
            status="blocked",
            target_url=target_url,
            blockers=blockers,
            raw_result=text,
            metadata={"verification_signal": False},
        )

    structured = parse_structured_result(text)
    if structured is not None:
        if structured.get("submitted") is True:
            return build_application_report(
                status="failed",
                target_url=target_url,
                blockers=("structured browser result claims submitted=true; manual review required",),
                raw_result=text,
                metadata={"submission_signal": True, "verification_signal": False},
            )
        fields = parse_field_audits(structured)
        metadata = audit_metadata(structured, fields)
        verified_fields = tuple(field.label for field in fields if field.verified)
        skipped_fields = tuple(field.label for field in fields if field.status in {"skipped", "manual", "conflict", "unmapped"})
        structured_blockers = tuple(
            str(item).strip() for item in structured.get("blockers", [])
            if str(item).strip()
        ) if isinstance(structured.get("blockers", []), list) else ()
        if structured_blockers:
            return build_application_report(
                status="blocked",
                target_url=target_url,
                filled_fields=verified_fields,
                skipped_fields=skipped_fields,
                blockers=structured_blockers,
                raw_result=text,
                metadata=metadata,
            )
        if verified_fields:
            return build_application_report(
                status="completed",
                target_url=target_url,
                filled_fields=verified_fields,
                skipped_fields=skipped_fields,
                raw_result=text,
                metadata=metadata,
            )
        return build_application_report(
            status="blocked",
            target_url=target_url,
            skipped_fields=skipped_fields,
            blockers=("structured browser result contained no verified fields",),
            raw_result=text,
            metadata=metadata,
        )

    if not text:
        return build_application_report(
            status="failed",
            target_url=target_url,
            blockers=("browser agent returned an empty result",),
            raw_result=text,
            metadata={"verification_signal": False},
        )

    if any(marker in lowered for marker in _EXPLICIT_VERIFICATION_MARKERS):
        return build_application_report(
            status="completed",
            target_url=target_url,
            raw_result=text,
            metadata={"verification_signal": True},
        )

    return build_application_report(
        status="blocked",
        target_url=target_url,
        blockers=("browser result did not explicitly verify a field change or upload",),
        raw_result=text,
        metadata={"verification_signal": False},
    )
