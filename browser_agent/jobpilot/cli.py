"""CLI entry point for the JobPilot MVP."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .models import JobDescription
from .profile import extract_resume_text, infer_contact_profile, load_contact_profile
from .workflow import JobPilot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JobPilot: ATS analysis and controlled browser autofill")
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Analyze a job and prepare application artifacts")
    prepare.add_argument("--title", required=True)
    prepare.add_argument("--company", required=True)
    prepare.add_argument("--description", required=True, help="Path to a text file containing the job description")
    prepare.add_argument("--url", default="")
    prepare.add_argument("--resume", required=True)
    prepare.add_argument("--profile", default="", help="Optional JSON contact profile")

    apply = sub.add_parser("apply", help="Open an application URL and safely autofill it")
    apply.add_argument("--title", required=True)
    apply.add_argument("--company", required=True)
    apply.add_argument("--description", required=True, help="Path to a text file containing the job description")
    apply.add_argument("--url", required=True)
    apply.add_argument("--resume", required=True)
    apply.add_argument("--profile", default="", help="Optional JSON contact profile")
    apply.add_argument("--model", default="gemini-3.6-flash")
    apply.add_argument("--max-steps", type=int, default=80)
    return parser


def _load_plan(args: argparse.Namespace):
    description = Path(args.description).expanduser().read_text(encoding="utf-8").strip()
    resume_text = extract_resume_text(args.resume)
    profile = load_contact_profile(args.profile) if args.profile else infer_contact_profile(resume_text)
    job = JobDescription(title=args.title, company=args.company, description=description, url=args.url)
    return JobPilot(model=getattr(args, "model", "gemini-3.6-flash"), max_steps=getattr(args, "max_steps", 80)).prepare_plan(
        job, resume_text, profile
    ), resume_text


async def _run(args: argparse.Namespace) -> int:
    plan, _ = _load_plan(args)
    if args.command == "prepare":
        print(json.dumps({
            "success": True,
            "score": plan.match.score,
            "matched_keywords": plan.match.matched_keywords,
            "missing_keywords": plan.match.missing_keywords,
            "cover_letter": plan.cover_letter,
            "auto_submit": plan.auto_submit,
        }, indent=2))
        return 0

    result = await JobPilot(model=args.model, max_steps=args.max_steps).apply_to_url(plan, resume_path=args.resume)
    final_result = getattr(result, "final_result", None)
    output = final_result() if callable(final_result) else str(result)
    print(json.dumps({"success": True, "result": output, "auto_submit": False}, indent=2))
    return 0


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
