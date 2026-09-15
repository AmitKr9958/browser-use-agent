"""Tests for JobPilot workbook ingestion."""

from openpyxl import Workbook

from browser_agent.jobpilot.job_source import get_job_posting_xlsx, load_job_postings_xlsx


def _write_workbook(path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append([
        "Company Name", "Job Title", "Location", "Job Posting URL", "Application URL", "Date Found", "Match Score", "Key Matching Skills", "Job Posting Date"
    ])
    sheet.append([
        "Weekday AI",
        "Power BI Lead",
        "Remote - India",
        "https://jobs.example.com/weekday-1/j/546035180F",
        "https://apply.example.com/weekday-1/546035180F",
        "2026-09-14",
        0.93,
        "Power BI, DAX, SQL",
        "2026-09-14",
    ])
    sheet.append(["", "", "", "", "", "", "", "", ""])
    workbook.save(path)


def test_load_job_postings_xlsx_normalizes_supported_columns(tmp_path) -> None:
    path = tmp_path / "jobs.xlsx"
    _write_workbook(path)
    postings = load_job_postings_xlsx(path)
    assert len(postings) == 1
    posting = postings[0]
    assert posting.row_number == 2
    assert posting.job.company == "Weekday AI"
    assert posting.job.title == "Power BI Lead"
    assert posting.job.location == "Remote - India"
    assert posting.job.url.endswith("546035180F")
    assert posting.application_url == "https://apply.example.com/weekday-1/546035180F"
    assert posting.job.description == "Power BI, DAX, SQL"
    assert posting.match_score == 0.93


def test_get_job_posting_xlsx_requires_excel_data_row(tmp_path) -> None:
    path = tmp_path / "jobs.xlsx"
    _write_workbook(path)
    posting = get_job_posting_xlsx(path, 2)
    assert posting.job.title == "Power BI Lead"
    assert posting.application_url.startswith("https://apply.example.com/")


def test_load_job_postings_xlsx_rejects_missing_required_header(tmp_path) -> None:
    workbook = Workbook()
    workbook.active.append(["Company Name", "Job Title"])
    path = tmp_path / "invalid.xlsx"
    workbook.save(path)
    try:
        load_job_postings_xlsx(path)
    except ValueError as exc:
        assert "Job Posting URL" in str(exc)
    else:
        raise AssertionError("expected missing-header validation")
