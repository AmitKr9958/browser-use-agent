"""Structured results for controlled job-application runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
