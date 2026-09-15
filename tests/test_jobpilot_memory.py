"""Regression tests for persistent, provenance-aware JobPilot memory."""

import json

from browser_agent.jobpilot.memory import (
    learned_answers,
    load_memory,
    lookup_answer,
    merge_profile,
    remember_correction,
    remember_user_value,
)
from browser_agent.jobpilot.models import ContactProfile


def test_user_profile_value_overrides_resume_value(tmp_path) -> None:
    path = tmp_path / "memory.json"
    assert remember_user_value(path, "phone", "+91 99999 11111") is True
    merged = merge_profile(ContactProfile(phone="+91 88888 22222"), path)
    assert merged.phone == "+91 99999 11111"


def test_question_answer_is_persisted_with_user_provenance(tmp_path) -> None:
    path = tmp_path / "memory.json"
    assert remember_user_value(path, "Notice period", "30 days") is True
    answers = learned_answers(path)
    assert answers["notice period"] == "30 days"
    stored = load_memory(path)
    assert stored["answers"]["notice period"]["source"] == "user"
    assert lookup_answer(path, "Notice-period") == "30 days"


def test_explicit_correction_replaces_previous_answer(tmp_path) -> None:
    path = tmp_path / "memory.json"
    assert remember_user_value(path, "Preferred name", "Amit Kumar") is True
    assert remember_correction(path, field="Preferred name", before_value="Amit Kumar", after_value="Amit") is True
    assert lookup_answer(path, "preferred name") == "Amit"


def test_sensitive_values_are_not_persisted(tmp_path) -> None:
    path = tmp_path / "memory.json"
    assert remember_user_value(path, "PAN number", "ABCDE1234F") is False
    assert not path.exists()


def test_memory_write_is_valid_json(tmp_path) -> None:
    path = tmp_path / "nested" / "memory.json"
    assert remember_user_value(path, "Work authorization", "Yes") is True
    json.loads(path.read_text(encoding="utf-8"))
