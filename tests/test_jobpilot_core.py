"""Unit tests for the JobPilot application layer."""

from __future__ import annotations

import pytest

from jobpilot.autofill import classify_field, map_form_fields
from jobpilot.models import Job, ResumeProfile
from jobpilot.pipeline import JobPilot


class FakeResponse:
    content = "GENERATED OUTPUT"


class FakeLLM:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def ainvoke(self, messages):
        self.prompts.append(messages[0].content)
        return FakeResponse()


@pytest.fixture
def profile() -> ResumeProfile:
    return ResumeProfile(
        name="Amit Kumar",
        email="amit@example.com",
        phone="+91 9000000000",
        location="Delhi, India",
        skills=["Python", "Automation"],
        links={"linkedin": "https://linkedin.com/in/example", "github": "https://github.com/example"},
    )


def test_classify_common_application_fields() -> None:
    assert classify_field("Email address") == "email"
    assert classify_field("Mobile Number") == "phone"
    assert classify_field("LinkedIn Profile") == "linkedin"
    assert classify_field("Unknown question") is None


def test_map_form_fields_uses_only_profile_values(profile: ResumeProfile) -> None:
    result = map_form_fields(["Full Name", "Email Address", "Work Authorization"], profile)
    assert result == {"Full Name": "Amit Kumar", "Email Address": "amit@example.com"}


@pytest.mark.asyncio
async def test_prepare_application_is_review_ready(profile: ResumeProfile) -> None:
    llm = FakeLLM()
    pilot = JobPilot(llm=llm)
    job = Job(title="Python Engineer", company="Example", url="https://example.com/job", description="Python automation")
    draft = await pilot.prepare_application(job, profile, "Amit Kumar\nPython\nAutomation")
    assert draft.ready_for_review is True
    assert draft.resume_markdown == "GENERATED OUTPUT"
    assert draft.cover_letter == "GENERATED OUTPUT"
    assert draft.autofill_fields["email"] == "amit@example.com"
    assert len(llm.prompts) == 2
    assert "never invent" in llm.prompts[0].casefold()
