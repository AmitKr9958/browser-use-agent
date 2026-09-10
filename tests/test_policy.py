"""Tests for production sensitive-interaction boundaries."""

from browser_agent.models.policy import SensitiveInteractionPolicy


def test_default_policy_requires_manual_sensitive_steps() -> None:
    text = SensitiveInteractionPolicy().instruction()
    assert "OTP/verification-code" in text
    assert "UPI PIN" in text
    assert "Aadhaar, PAN" in text
    assert "passwords" in text


def test_policy_can_disable_individual_boundaries() -> None:
    text = SensitiveInteractionPolicy(
        require_manual_otp=False,
        require_manual_payment_auth=False,
        require_manual_identity_ids=False,
        require_manual_passwords=False,
    ).instruction()
    assert "Never invent, guess, or fabricate" in text
    assert "OTP/verification-code" not in text
    assert "UPI PIN" not in text
    assert "Aadhaar, PAN" not in text
