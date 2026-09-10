"""Safety and interaction boundaries for production browser automation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SensitiveInteractionPolicy:
    """Controls steps that should remain under explicit user control.

    The agent may navigate to a sensitive step, but the default policy tells the
    model not to invent, disclose, or submit high-risk authentication/identity data.
    """

    require_manual_otp: bool = True
    require_manual_payment_auth: bool = True
    require_manual_identity_ids: bool = True
    require_manual_passwords: bool = True

    def instruction(self) -> str:
        rules: list[str] = [
            "Use only values supplied by the user or already present in the authorized form context.",
            "Never invent, guess, or fabricate personal, identity, financial, or authentication data.",
        ]
        if self.require_manual_otp:
            rules.append("Stop at OTP/verification-code entry and require the user to provide or complete it manually.")
        if self.require_manual_payment_auth:
            rules.append("Do not enter or submit UPI PIN, card PIN, CVV, or other payment authorization secrets.")
        if self.require_manual_identity_ids:
            rules.append("Do not invent or infer Aadhaar, PAN, passport, driving-licence, or other government ID values.")
        if self.require_manual_passwords:
            rules.append("Do not expose, log, or invent passwords; leave password entry to the user's approved credential mechanism.")
        return "Sensitive interaction policy:\n- " + "\n- ".join(rules)


DEFAULT_SENSITIVE_POLICY = SensitiveInteractionPolicy()
