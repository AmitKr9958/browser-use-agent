"""High-level JobPilot orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .ats import detect_ats
from .browser_autofill import autofill_page, inspect_form, plan_autofill
from .generator import generate_cover_letter, generate_resume
from .matching import match_keywords
from .models import ApplicationReview, Job, JobApplicationDraft, ResumeProfile
from .providers import create_llm
from .resume_io import write_ats_docx


class JobPilot:
    """Prepare and safely autofill an application without submitting it."""

    def __init__(self, *, provider: str = "google", model: str = "gemini-3.6-flash", llm: Any | None = None) -> None:
        self.llm = llm if llm is not None else create_llm(provider, model)

    async def prepare_application(
        self,
        job: Job,
        profile: ResumeProfile,
        current_resume: str,
    ) -> JobApplicationDraft:
        """Generate tailored material and deterministic autofill data; do not submit."""
        matched, missing = match_keywords(job, profile)
        resume = await generate_resume(self.llm, job, profile, current_resume)
        cover_letter = await generate_cover_letter(self.llm, job, profile, resume)
        return JobApplicationDraft(
            job=job,
            resume_markdown=resume,
            cover_letter=cover_letter,
            matched_keywords=matched,
            missing_requirements=missing,
            autofill_fields=self._autofill_fields(profile),
            ready_for_review=True,
        )

    async def prepare_and_autofill(
        self,
        job: Job,
        profile: ResumeProfile,
        current_resume: str,
        page: Any,
        *,
        resume_path: str | Path | None = None,
        cover_letter_path: str | Path | None = None,
    ) -> ApplicationReview:
        """Prepare materials, fill safe empty fields, and stop before submission.

        The browser page is supplied by the caller so Browser Use can keep control
        of the user's existing session. Unknown and sensitive fields are left alone.
        """
        draft = await self.prepare_application(job, profile, current_resume)
        fields = await inspect_form(page)
        plan = plan_autofill(fields, profile)
        filled = await autofill_page(page, profile)
        planned_indexes = {index for index, _, _ in plan}

        skipped: list[dict[str, str | int]] = []
        unknown: list[dict[str, str | int]] = []
        for field in fields:
            index = int(field["index"])
            if index in planned_indexes:
                continue
            label = next(
                (
                    str(field.get(key, "")).strip()
                    for key in ("name", "id", "placeholder", "autocomplete", "aria")
                    if str(field.get(key, "")).strip()
                ),
                f"field-{index}",
            )
            field_type = str(field.get("type", "")).casefold()
            if field_type in {"hidden", "submit", "button"}:
                skipped.append({"index": index, "field": label, "reason": "non-data control"})
            else:
                unknown.append({"index": index, "field": label, "reason": "not confidently mapped"})

        written_resume: str | None = None
        written_cover: str | None = None
        if resume_path is not None:
            output = Path(resume_path).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            write_ats_docx(draft.resume_markdown, output)
            written_resume = str(output)
        if cover_letter_path is not None:
            output = Path(cover_letter_path).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(draft.cover_letter, encoding="utf-8")
            written_cover = str(output)

        page_url = str(getattr(page, "url", "") or job.application_url or job.url)
        ats = str(job.ats or detect_ats(urlparse(page_url).geturl()))
        return ApplicationReview(
            draft=draft,
            ats=ats,
            filled_fields=filled,
            skipped_fields=skipped,
            unknown_fields=unknown,
            resume_path=written_resume,
            cover_letter_path=written_cover,
            ready_for_review=True,
            submitted=False,
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
