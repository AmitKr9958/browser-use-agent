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
from .memory import default_memory_path, learned_answers, merge_profile, remember_correction
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
    prepare.add_argument("--description", required=True)
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
    apply.add_argument("--description", required=True)
    apply.add_argument("--url", required=True)
    apply.add_argument("--resume", required=True)
    apply.add_argument("--profile", default="")
    apply.add_argument("--memory", default=memory_default, help="Persistent JobPilot memory JSON")
    apply.add_argument("--model", default="gemini-3.6-flash")
    apply.add_argument("--max-steps", type=int, default=80)
    return parser


def _load_inputs(args: argparse.Namespace) -> tuple[JobDescription, str, ContactProfile]:
    description = Path(args.description).expanduser().read_text(encoding="utf-8").strip()
    resume_text = extract_resume_text(args.resume)
    profile = load_contact_profile(args.profile) if args.profile else infer_contact_profile(resume_text)
    profile = merge_profile(profile, args.memory)
    job = JobDescription(title=args.title, company=args.company, description=description, url=args.url)
    return job, resume_text, profile


def _apply_memory(plan, memory_path: str):
    if not memory_path:
        return plan
    answers = dict(plan.answers)
    for question, answer in learned_answers(memory_path).items():
        answers.setdefault(question, answer)
    return replace(plan, answers=answers)


def _persist_explicit_corrections(raw_result: str, memory_path: str) -> int:
    """Learn only corrections explicitly attributed to the user by the browser audit."""
    if not memory_path:
        return 0
    data = parse_structured_result(raw_result)
    if not data:
        return 0
    corrections = data.get("corrections", [])
    if not isinstance(corrections, list):
        return 0
    persisted = 0
    for item in corrections:
        if not isinstance(item, dict) or item.get("source") != "user" or item.get("explicit") is not True:
            continue
        field = str(item.get("field", "")).strip()
        before = str(item.get("before_value", "")).strip()
        after = str(item.get("after_value", "")).strip()
        if remember_correction(memory_path, field=field, before_value=before, after_value=after, reason=str(item.get("reason", ""))):
            persisted += 1
    return persisted


def _write_artifacts(plan, output_dir: str) -> dict[str, str]:
    if not output_dir:
        return {}
    directory = Path(output_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    resume_txt = directory / "tailored_resume_draft.txt"
    resume_docx = directory / "tailored_resume_draft.docx"
    cover_out = directory / "cover_letter.txt"
    resume_txt.write_text(plan.tailored_resume_text, encoding="utf-8")
    write_resume_docx(plan.tailored_resume_text, resume_docx)
    cover_out.write_text(plan.cover_letter, encoding="utf-8")
    return {
        "tailored_resume_text": str(resume_txt),
        "tailored_resume_docx": str(resume_docx),
        "cover_letter": str(cover_out),
    }


def _plan_output(plan, artifacts: dict[str, str]) -> dict[str, object]:
    return {
        "success": True,
        "score": plan.match.score,
        "matched_keywords": plan.match.matched_keywords,
        "missing_keywords": plan.match.missing_keywords,
        "tailored_resume": plan.tailored_resume_text,
        "cover_letter": plan.cover_letter,
        "artifacts": artifacts,
        "auto_submit": plan.auto_submit,
        "learned_answers": len(plan.answers),
    }


async def _run_workbook(args: argparse.Namespace) -> int:
    posting = get_job_posting_xlsx(args.file, args.row)
    resume_text = extract_resume_text(args.resume)
    profile = load_contact_profile(args.profile) if args.profile else infer_contact_profile(resume_text)
    profile = merge_profile(profile, args.memory)
    pilot = JobPilot(model=args.model, max_steps=args.max_steps)
    job = posting.job
    application_url = posting.application_url or posting.job.url
    extraction = {"attempted": False, "verified": False}
    if args.apply:
        extraction["attempted"] = True
        job = await extract_job_description_from_url(
            posting.job.url,
            model=args.model,
            max_steps=min(args.max_steps, 40),
        )
        job = replace(job, url=application_url)
        extraction["verified"] = True
    plan = await pilot.prepare_plan_async(job, resume_text, profile, use_llm=not args.no_llm)
    plan = _apply_memory(plan, args.memory)
    output = {
        "source": {
            "file": str(Path(args.file).expanduser()),
            "row": posting.row_number,
            "workbook_match_score": posting.match_score,
            "job_url": posting.job.url,
            "application_url": application_url,
        },
        "job": asdict(job),
        "job_extraction": extraction,
        "plan": _plan_output(plan, _write_artifacts(plan, args.output_dir)),
    }
    if args.apply:
        result = await pilot.apply_to_url(plan, resume_path=args.resume)
        final_result = getattr(result, "final_result", None)
        raw_result = str(final_result()) if callable(final_result) else str(result)
        report = build_application_report_from_result(target_url=application_url, raw_result=raw_result)
        learned = _persist_explicit_corrections(raw_result, args.memory)
        output["application"] = {
            "status": report.status,
            "filled_fields": report.filled_fields,
            "skipped_fields": report.skipped_fields,
            "blockers": report.blockers,
            "submitted": report.submitted,
            "result": report.raw_result,
            "metadata": report.metadata,
            "learned_corrections": learned,
        }
        print(json.dumps(output, indent=2))
        return 0 if report.status in {"completed", "blocked"} else 1
    print(json.dumps(output, indent=2))
    return 0


async def _run(args: argparse.Namespace) -> int:
    if args.command == "workbook":
        return await _run_workbook(args)
    job, resume_text, profile = _load_inputs(args)
    pilot = JobPilot(model=args.model, max_steps=args.max_steps)
    if args.command == "prepare":
        plan = await pilot.prepare_plan_async(job, resume_text, profile, use_llm=not args.no_llm)
        plan = _apply_memory(plan, args.memory)
        print(json.dumps(_plan_output(plan, _write_artifacts(plan, args.output_dir)), indent=2))
        return 0
    plan = _apply_memory(pilot.prepare_plan(job, resume_text, profile), args.memory)
    result = await pilot.apply_to_url(plan, resume_path=args.resume)
    final_result = getattr(result, "final_result", None)
    output = str(final_result()) if callable(final_result) else str(result)
    report = build_application_report_from_result(target_url=job.url, raw_result=output)
    learned = _persist_explicit_corrections(output, args.memory)
    print(
        json.dumps(
            {
                "success": report.status in {"completed", "blocked"},
                "status": report.status,
                "filled_fields": report.filled_fields,
                "skipped_fields": report.skipped_fields,
                "blockers": report.blockers,
                "submitted": report.submitted,
                "result": report.raw_result,
                "metadata": report.metadata,
                "learned_corrections": learned,
            },
            indent=2,
        )
    )
    return 0 if report.status in {"completed", "blocked"} else 1


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
