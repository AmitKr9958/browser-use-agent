"""CLI entry point for the JobPilot MVP."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, replace
from pathlib import Path

from .application import build_application_report_from_result
from .audit import parse_structured_result
from .documents import write_resume_docx
from .job_source import get_job_posting_xlsx
from .memory import default_memory_path, learned_answers, lookup_answer, merge_profile, remember_correction
from .models import ContactProfile, JobDescription
from .profile import extract_resume_text, infer_contact_profile, load_contact_profile
from .workflow import JobPilot, extract_job_description_from_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JobPilot: ATS analysis and controlled browser autofill")
    sub = parser.add_subparsers(dest="command", required=True)
    memory_default = str(default_memory_path())

    prepare = sub.add_parser("prepare", help="Analyze a job and prepare application artifacts")
    prepare.add_argument("--title", required=True)
    prepare.add_argument("--company", required=True)
    prepare.add_argument("--description", required=True, help="Job description text or path to a UTF-8 text file")
    prepare.add_argument("--url", default="")
    prepare.add_argument("--resume", required=True)
    prepare.add_argument("--profile", default="")
    prepare.add_argument("--memory", default=memory_default, help="Persistent JobPilot memory JSON")
    prepare.add_argument("--model", default="gemini-3.6-flash")
    prepare.add_argument("--max-steps", type=int, default=80)
    prepare.add_argument("--output-dir", default="")
    prepare.add_argument("--no-llm", action="store_true")

    workbook = sub.add_parser("workbook", help="Prepare or safely apply to a job selected from an XLSX workbook")
    workbook.add_argument("--file", required=True)
    workbook.add_argument("--row", required=True, type=int)
    workbook.add_argument("--resume", required=True)
    workbook.add_argument("--profile", default="")
    workbook.add_argument("--memory", default=memory_default, help="Persistent JobPilot memory JSON")
    workbook.add_argument("--model", default="gemini-3.6-flash")
    workbook.add_argument("--max-steps", type=int, default=80)
    workbook.add_argument("--output-dir", default="")
    workbook.add_argument("--no-llm", action="store_true")
    workbook.add_argument("--apply", action="store_true")

    apply = sub.add_parser("apply", help="Open an application URL and safely autofill it")
    apply.add_argument("--title", required=True)
    apply.add_argument("--company", required=True)
    apply.add_argument("--description", required=True, help="Job description text or path to a UTF-8 text file")
    apply.add_argument("--url", required=True)
    apply.add_argument("--resume", required=True)
    apply.add_argument("--profile", default="")
    apply.add_argument("--memory", default=memory_default, help="Persistent JobPilot memory JSON")
    apply.add_argument("--model", default="gemini-3.6-flash")
    apply.add_argument("--max-steps", type=int, default=80)
    return parser


def _load_inputs(args: argparse.Namespace) -> tuple[JobDescription, str, ContactProfile]:
    description_arg = str(args.description).strip()
    description_path = Path(description_arg).expanduser()
    if description_path.is_file():
        description = description_path.read_text(encoding="utf-8").strip()
    else:
        description = description_arg
    if not description:
        raise ValueError("job description must not be empty")
    resume_text = extract_resume_text(args.resume)
    profile_path = getattr(args, "profile", "")
    memory_path = getattr(args, "memory", "")
    title = getattr(args, "title", "")
    company = getattr(args, "company", "")
    url = getattr(args, "url", "")
    profile = load_contact_profile(profile_path) if profile_path else infer_contact_profile(resume_text)
    profile = merge_profile(profile, memory_path)
    job = JobDescription(title=title, company=company, description=description, url=url)
    return job, resume_text, profile


def _apply_memory(plan, memory_path: str):
    """Overlay learned answers only when the current question resolves to that memory key.

    Explicit answers already present in the plan always win. Semantic lookup is
    intentionally conservative: memory itself decides whether two question labels
    normalize to the same key, avoiding broad fuzzy matching that could mis-answer
    sensitive application questions.
    """
    if not memory_path:
        return plan
    answers = dict(plan.answers)
