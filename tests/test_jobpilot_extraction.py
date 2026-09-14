"""Tests for read-only job-description extraction parsing."""

import pytest

from browser_agent.jobpilot.models import JobDescription
from browser_agent.jobpilot.workflow import _parse_job_description_result, build_job_extraction_task


def test_parse_job_description_json() -> None:
    job = _parse_job_description_result(
        '{"title":"Power BI Lead","company":"Weekday AI","location":"Remote - India","description":"Power BI, DAX, SQL"}',
        url="https://example.com/job",
        fallback=JobDescription(title="fallback", company="fallback", description="fallback", url="https://example.com/job"),
    )
    assert job.title == "Power BI Lead"
    assert job.company == "Weekday AI"
    assert job.location == "Remote - India"
    assert job.description == "Power BI, DAX, SQL"


def test_parse_job_description_rejects_incomplete_result() -> None:
    with pytest.raises(ValueError, match="incomplete"):
        _parse_job_description_result(
            '{"title":"Power BI Lead","company":"Weekday AI","location":"","description":""}',
            url="https://example.com/job",
            fallback=JobDescription(title="fallback", company="fallback", description="fallback", url="https://example.com/job"),
        )


def test_job_extraction_task_is_read_only() -> None:
    task = build_job_extraction_task("https://example.com/job")
    assert "Do not click Apply" in task
    assert "Return ONLY valid JSON" in task
    assert "https://example.com/job" in task
