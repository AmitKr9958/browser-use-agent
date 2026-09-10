"""JobPilot application layer built on Browser Use."""

from .models import Job, JobApplicationDraft, ResumeProfile
from .pipeline import JobPilot

__all__ = ["Job", "JobApplicationDraft", "JobPilot", "ResumeProfile"]
