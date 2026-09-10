"""Tests for deterministic browser form autofill planning."""

from jobpilot.browser_autofill import plan_autofill
from jobpilot.models import ResumeProfile


def test_plan_autofill_skips_sensitive_and_existing_fields() -> None:
    profile = ResumeProfile(name="Amit Kumar", email="amit@example.com", phone="+91 9000000000")
    fields = [
        {"index": 0, "type": "text", "name": "full_name", "id": "", "placeholder": "", "autocomplete": "", "aria": "", "value": ""},
        {"index": 1, "type": "email", "name": "email", "id": "", "placeholder": "", "autocomplete": "", "aria": "", "value": "existing@example.com"},
        {"index": 2, "type": "password", "name": "password", "id": "", "placeholder": "", "autocomplete": "", "aria": "", "value": ""},
    ]
    assert plan_autofill(fields, profile) == [(0, "name", "Amit Kumar")]
