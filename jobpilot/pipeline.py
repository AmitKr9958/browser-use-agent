"""High-level JobPilot orchestration."""

from __future__ import annotations

from typing import Any

from .generator import generate_cover_letter, generate_resume
from .models import Job, JobApplicationDraft, ResumeProfile
from .providers import create_llm


class JobPilot:
    """Prepare a tailored application from a job, profile, and current resume."""

    def __init__(self, *, provider: str = "google", model: str = "gemini-3.6-flash", llm: Any | None = None) -> None:
        self.llm = llm if llm is not None else create_llm(provider, model)

    async def prepare_application(
        self,
        job: Job,
        profile: ResumeProfile,
        current_resume: str,
    ) -> JobApplicationDraft:
        """Generate the resume and cover letter; do not submit an application."""
        resume = await generate_resume(self.llm, job, profile, current_resume)
        cover_letter = await generate_cover_letter(self.llm, job, profile, resume)
        return JobApplicationDraft(
            job=job,
            resume_markdown=resume,
            cover_letter=cover_letter,
            autofill_fields=self._autofill_fields(profile),
            ready_for_review=True,
        )

    @staticmethod
    def _autofill_fields(profile: ResumeProfile) -> dict[str, str]:
        """Return only deterministic fields backed by explicit candidate data."""
        fields: dict[str, str] = {"name": profile.name, "email": profile.email}
        optional = {
            "phone": profile.phone,
            "location": profile.location,
            "linkedin": profile.links.get("linkedin"),
            "github": profile.links.get("github"),
        }
        fields.update({key: value for key, value in optional.items() if value})
        return fields
