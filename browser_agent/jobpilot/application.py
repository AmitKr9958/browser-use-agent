"""Structured results for controlled job-application runs."""

from __future__ import annotations

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
_VERIFICATION_MARKERS = (
    "verified",
    "filled",
    "attached",
    "uploaded",
    "saved",
    "review",
)


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
        raw_result=raw_result,
        metadata=dict(metadata or {}),
    )
    report.validate()
    return report


def build_application_report_from_result(*, target_url: str, raw_result: str) -> ApplicationReport:
    """Convert an agent result into a conservative report.

    A browser-agent response is not proof that fields were actually changed. The
    report is therefore only marked ``completed`` when the response contains an
    explicit verification signal. Submission language is treated as a safety
    failure instead of being accepted as a successful application.
    """
    text = raw_result.strip()
    lowered = text.lower()

    if any(marker in lowered for marker in _SUBMISSION_MARKERS):
        return build_application_report(
            status="failed",
            target_url=target_url,
            blockers=("agent result indicates a submission may have occurred; manual review required",),
            raw_result=text,
            metadata={"submission_signal": True},
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

    if any(marker in lowered for marker in _VERIFICATION_MARKERS):
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
