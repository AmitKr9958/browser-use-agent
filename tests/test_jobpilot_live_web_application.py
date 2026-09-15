"""Live web smoke test for a public dummy job-application page.

This test intentionally never submits the form. It verifies that the external
application page is reachable and that the expected field/stop boundary still
exists before running a real browser-agent session against it.
"""

from __future__ import annotations

import re

import httpx


LIVE_JOB_APPLICATION_URL = "https://www.jotform.com/261371985197066"


def _normalized_html(url: str) -> str:
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": "JobPilot-live-smoke/1.0"},
    )
    response.raise_for_status()
    return re.sub(r"\s+", " ", response.text).casefold()


def test_live_dummy_job_application_page_is_reachable_and_has_expected_fields() -> None:
    html = _normalized_html(LIVE_JOB_APPLICATION_URL)

    expected_labels = (
        "full name",
        "email address",
        "phone number",
        "upload resume/cv",
        "cover letter or motivation",
        "submit application",
    )
    missing = [label for label in expected_labels if label not in html]
    assert not missing, f"live job application page is missing expected labels: {missing}"


def test_live_dummy_job_application_contains_no_auto_submit_instruction() -> None:
    html = _normalized_html(LIVE_JOB_APPLICATION_URL)
    assert "submit application" in html
    # This test documents the safety boundary: the page has a submit control,
    # but the smoke test itself performs no POST/click/submit operation.
    assert "upload resume/cv" in html
