"""Tests for the end-to-end JobPilot preparation flow."""

from types import SimpleNamespace

import pytest

from jobpilot import Job, JobPilot, ResumeProfile


class _Response:
    def __init__(self, content: str) -> None:
        self.content = content


class _LLM:
    def __init__(self) -> None:
        self.calls = 0

    async def ainvoke(self, messages: object) -> _Response:
        self.calls += 1
        if self.calls == 1:
            return _Response("# Amit Kumar\n\n## Skills\nPython, SQL")
        return _Response("Dear Hiring Team,\n\nI am interested in this role.")


class _Page:
    url = "https://boards.greenhouse.io/example/jobs/1"

    def __init__(self) -> None:
        self.values: dict[int, str] = {}
        self.submitted = False

    async def evaluate(self, script: str, arg: object = None) -> str | bool:
        if "JSON.stringify" in script:
            import json

            return json.dumps([
                {"index": 0, "tag": "input", "type": "text", "name": "full_name", "id": "", "placeholder": "", "autocomplete": "", "aria": "", "value": ""},
                {"index": 1, "tag": "input", "type": "email", "name": "email", "id": "", "placeholder": "", "autocomplete": "", "aria": "", "value": ""},
                {"index": 2, "tag": "input", "type": "password", "name": "password", "id": "", "placeholder": "", "autocomplete": "", "aria": "", "value": ""},
            ])
        assert isinstance(arg, dict)
        self.values[int(arg["index"])] = str(arg["value"])
        return True


@pytest.mark.asyncio
async def test_prepare_and_autofill_stops_before_submission(tmp_path) -> None:
    llm = _LLM()
    pilot = JobPilot(llm=llm)
    page = _Page()
    profile = ResumeProfile(name="Amit Kumar", email="amit@example.com", phone="+91 9000000000")
    job = Job(title="Python Engineer", company="Example", url=page.url, description="Python SQL")

    result = await pilot.prepare_and_autofill(
        job,
        profile,
        "Amit Kumar\nPython developer",
        page,
        resume_path=tmp_path / "resume.docx",
        cover_letter_path=tmp_path / "cover-letter.txt",
    )

    assert result.ats == "greenhouse"
    assert result.submitted is False
    assert result.ready_for_review is True
    assert [item["field"] for item in result.filled_fields] == ["name", "email"]
    assert result.unknown_fields
    assert page.values == {0: "Amit Kumar", 1: "amit@example.com"}
    assert page.submitted is False
    assert (tmp_path / "resume.docx").is_file()
    assert (tmp_path / "cover-letter.txt").is_file()
    assert llm.calls == 2
