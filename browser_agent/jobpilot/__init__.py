"""JobPilot: job-aware, safety-first application assistance built on Browser Use."""

from .application import ApplicationReport, build_application_report
from .ats import score_job_match
from .documents import (
    build_cover_letter,
    build_cover_letter_with_llm,
    tailor_resume_text,
    tailor_resume_with_llm,
    write_resume_docx,
)
from .models import ApplicationPlan, ContactProfile, JobDescription
from .profile import extract_resume_text, infer_contact_profile, load_contact_profile
from .workflow import JobPilot, build_application_task

__all__ = [
    "ApplicationPlan",
    "ApplicationReport",
    "ContactProfile",
    "JobDescription",
    "JobPilot",
    "build_application_report",
    "build_application_task",
    "build_cover_letter",
    "build_cover_letter_with_llm",
    "extract_resume_text",
    "infer_contact_profile",
    "load_contact_profile",
    "score_job_match",
    "tailor_resume_text",
    "tailor_resume_with_llm",
    "write_resume_docx",
]
