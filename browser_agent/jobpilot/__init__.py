"""JobPilot MVP: job-aware, safety-first application assistance built on Browser Use."""

from .ats import score_job_match
from .documents import build_cover_letter, tailor_resume_text
from .models import ApplicationPlan, ContactProfile, JobDescription
from .profile import extract_resume_text, load_contact_profile
from .workflow import JobPilot, build_application_task

__all__ = [
    "ApplicationPlan",
    "ContactProfile",
    "JobDescription",
    "JobPilot",
    "build_application_task",
    "build_cover_letter",
    "extract_resume_text",
    "load_contact_profile",
    "score_job_match",
    "tailor_resume_text",
]
