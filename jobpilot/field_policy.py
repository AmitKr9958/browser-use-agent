"""Conservative application-field policy for rapid, reviewable autofill."""

from __future__ import annotations

SENSITIVE_TOKENS = (
    "otp", "one time password", "password", "credit card", "cvv", "bank account",
    "aadhaar", "pan number", "passport", "tax id", "government id",
)


def is_safe_autofill_label(label: str) -> bool:
    """Return True only when the field is not obviously sensitive."""
    normalized = " ".join(label.casefold().split())
    return not any(token in normalized for token in SENSITIVE_TOKENS)
