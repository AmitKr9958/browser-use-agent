"""JobPilot application layer built on Browser Use."""

from .ats import ATS, detect_ats
from .autofill import build_field_values, classify_field, map_form_fields
from .browser_upload import upload_file_by_dom_index
from .career_pages import CareerPage, CareerPageRegistry
from .field_policy import is_safe_autofill_label
from .generator import answer_application_question
from .models import ApplicationReview, Job, JobApplicationDraft, ResumeProfile
from .pipeline import JobPilot
from .resume_io import read_resume, write_ats_docx
from .resume_quality import ResumeQuality, validate_ats_resume

__all__ = [
    "ATS", "ApplicationReview", "CareerPage", "CareerPageRegistry", "Job",
    "JobApplicationDraft", "JobPilot", "ResumeProfile", "ResumeQuality",
    "answer_application_question", "build_field_values", "classify_field", "detect_ats",
    "is_safe_autofill_label", "map_form_fields", "read_resume", "upload_file_by_dom_index",
    "validate_ats_resume", "write_ats_docx",
]
