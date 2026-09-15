"""Tests for deterministic JobPilot browser audit/reconciliation."""

from browser_agent.jobpilot.audit import (
    audit_metadata,
    parse_corrections,
    parse_field_audits,
    parse_structured_result,
    reconcile_fields,
)
from browser_agent.jobpilot.application import build_application_report_from_result


def _result() -> str:
    return '''{
      "final_page": "Review",
      "fields": [
        {"label":"Full Name","type":"input","planned_value":"Amit Kumar","observed_value":"Amit Kumar","source":"resume","status":"filled","verified":true,"step":"1"},
        {"label":"Notice Period","type":"input","planned_value":"30 days","observed_value":"60 days","source":"existing_page","status":"conflict","verified":false,"reason":"existing value preserved","step":"2"}
      ],
      "corrections": [{"field":"Preferred name","before_value":"Amit Kumar","after_value":"Amit","source":"user","explicit":true,"reason":"user corrected it","step":"2"}],
      "blockers": [],
      "final_submission_control_present": true,
      "submitted": false
    }'''


def test_structured_result_reconciles_verified_fields() -> None:
    data = parse_structured_result(_result())
    assert data is not None
    fields = parse_field_audits(data)
    reconciled = reconcile_fields(fields)
    assert reconciled[0].verified is True
    assert reconciled[1].status == "conflict"
    assert parse_corrections(data)[0].explicit is True


def test_audit_metadata_contains_review_state() -> None:
    data = parse_structured_result(_result())
    assert data is not None
    metadata = audit_metadata(data, parse_field_audits(data))
    assert metadata["final_submission_control_present"] is True
    assert len(metadata["corrections"]) == 1


def test_application_report_uses_structured_audit_without_submission() -> None:
    report = build_application_report_from_result(target_url="https://example.com/apply", raw_result=_result())
    assert report.status == "completed"
    assert report.submitted is False
    assert report.filled_fields == ("Full Name",)
    assert report.skipped_fields == ("Notice Period",)
    assert report.metadata["final_submission_control_present"] is True


def test_invalid_user_correction_is_ignored() -> None:
    data = parse_structured_result('{"corrections":[{"field":"x","after_value":"y","source":"agent","explicit":true}]}')
    assert data is not None
    assert parse_corrections(data) == ()
