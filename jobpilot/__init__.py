"""JobPilot application layer built on Browser Use."""

from .autofill import build_field_values, classify_field, map_form_fields
from .models import Job, JobApplicationDraft, ResumeProfile
from .pipeline import JobPilot
from .resume_io import read_resume, write_ats_docx

__all__ = [
    "Job",
    "JobApplicationDraft",
    "JobPilot",
    "ResumeProfile",
    "build_field_values",
    "classify_field",
    "map_form_fields",
    "read_resume",
    "write_ats_docx",
]
