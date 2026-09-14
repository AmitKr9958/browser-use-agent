"""Structured results for controlled job-application runs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


_SUBMISSION_MARKERS = (
    "application submitted",
    "successfully submitted",
    "submission successful",
    "submitted successfully",
    "application has been submitted",
)
_BLOCKER_MARKERS = (
    "captcha",
    "mfa",
    "otp",
    "verification code",
    "login required",
    "payment required",
    "identity verification",
)
# Generic words such as "saved" or "filled" are intentionally excluded: an
# agent can say those words without proving that a browser control changed.
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
_SECRET_RE = re.compile(r"\b(?:password|passwd|otp|one[- ]time code|verification code)\s*[:=]\s*\S+", re.IGNORECASE)
_MAX_RAW_RESULT = 8_000


def _sanitize_result(text: str) -> str:
    """Remove common personal/secret values before a result is persisted or printed."""
    sanitized = _SECRET_RE.sub(lambda match: f"{match.group(0).split(':', 1)[0]}: [REDACTED]", text)
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
    """Construct and validate an application report."""
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
    """Convert an agent result into a conservative, privacy-aware report.

    A browser-agent response is not proof that fields were actually changed. The
    report is only marked ``completed`` when an explicit verification signal is
    present. Submission language is treated as a safety failure.
    """
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

    blockers = tuple(marker for marker in _BLOCKER_MARKERS if marker in lowered)
    if blockers:
        return build_application_report(
            status="blocked",
            target_url=target_url,
            blockers=blockers,
            raw_result=text,
            metadata={"verification_signal": False},
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
