"""ATS detection and application-platform strategy selection."""

from __future__ import annotations

from enum import StrEnum


class ATS(StrEnum):
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WORKDAY = "workday"
    ASHBY = "ashby"
    ICIMS = "icims"
    SMARTRECRUITERS = "smartrecruiters"
    TALEO = "taleo"
    ORACLE = "oracle"
    SAP = "sap"
    CUSTOM = "custom"
    UNKNOWN = "unknown"

_SIGNATURES: dict[ATS, tuple[str, ...]] = {
    ATS.GREENHOUSE: ("greenhouse.io", "boards.greenhouse.io"),
    ATS.LEVER: ("jobs.lever.co", "lever.co"),
    ATS.WORKDAY: ("myworkdayjobs.com", "workday.com"),
    ATS.ASHBY: ("jobs.ashbyhq.com", "ashbyhq.com"),
    ATS.ICIMS: ("icims.com",),
    ATS.SMARTRECRUITERS: ("smartrecruiters.com",),
    ATS.TALEO: ("taleo.net",),
    ATS.ORACLE: ("oraclecloud.com",),
    ATS.SAP: ("successfactors.com",),
}


def detect_ats(url: str, html: str = "") -> ATS:
    """Identify common ATS platforms from URL/HTML without an LLM call."""
    haystack = f"{url}\n{html}".casefold()
    for ats, signatures in _SIGNATURES.items():
        if any(signature in haystack for signature in signatures):
            return ats
    return ATS.CUSTOM if html else ATS.UNKNOWN
