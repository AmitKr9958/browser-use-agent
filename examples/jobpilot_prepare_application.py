"""Prepare a tailored resume and cover letter from an existing resume.

Set GOOGLE_API_KEY (or another provider's credentials) before running.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from jobpilot import Job, JobPilot, ResumeProfile, read_resume, write_ats_docx


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", required=True, help="Existing PDF/DOCX/TXT/Markdown resume")
    parser.add_argument("--job-url", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--phone")
    parser.add_argument("--location")
    parser.add_argument("--output", default="jobpilot-output/resume-tailored.docx")
    args = parser.parse_args()
    load_dotenv()

    profile = ResumeProfile(name=args.name, email=args.email, phone=args.phone, location=args.location)
    job = Job(title=args.title, company=args.company, url=args.job_url, description=args.description)
    current_resume = read_resume(args.resume)
    draft = await JobPilot().prepare_application(job, profile, current_resume)
    output = write_ats_docx(draft.resume_markdown, Path(args.output))
    Path(args.output).with_suffix(".cover-letter.txt").write_text(draft.cover_letter, encoding="utf-8")
    print(f"ATS resume: {output}")
    print(f"Matched keywords: {', '.join(draft.matched_keywords[:20])}")
    print("Application draft is ready for review; no submission was performed.")


if __name__ == "__main__":
    asyncio.run(main())
