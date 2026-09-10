# JobPilot application layer

JobPilot is the application layer built on top of Browser Use. Browser Use remains the general-purpose browser execution engine.

## Production flow

1. Load a normalized `Job` from the application's career-page/job database.
2. Load the candidate's `ResumeProfile` and current resume.
3. Generate a truthful, ATS-friendly tailored resume and cover letter.
4. Detect the application platform from the URL/HTML when possible.
5. Inspect the open application form.
6. Fill only empty fields that are confidently mapped to explicit profile facts.
7. Leave sensitive, ambiguous, and unsupported questions for review.
8. Optionally upload the generated resume using an explicitly identified Browser Use DOM file-input index.
9. Return an auditable `ApplicationReview` manifest.
10. Stop. `submitted` is always false in the JobPilot application layer; final submission remains a human action.

## Why the flow is split

The fast path is deterministic: common ATS fields such as name, email, phone, LinkedIn, and GitHub are mapped without an LLM call. The LLM is reserved for resume tailoring, cover letters, and safe fallback questions. This reduces latency and avoids asking a model to guess routine form fields.

## Supported ATS detection

The detector recognizes common URL/HTML signatures for Greenhouse, Lever, Workday, Ashby, iCIMS, SmartRecruiters, Taleo, Oracle, and SAP SuccessFactors. Unknown application sites are treated as custom/unknown rather than guessed.

## Safety boundary

JobPilot never supplies passwords, OTPs, payment details, Aadhaar/PAN/passport/government identifiers, or similar sensitive values. Existing non-empty form values are preserved. Automatic submission is intentionally not implemented.

## Browser Use file upload

Use `upload_file_by_dom_index(browser_session, index, path)` only after the application page's file input has been explicitly identified. It dispatches Browser Use's native `UploadFileEvent`; it does not click or submit the application form.

## Example

The existing `examples/jobpilot_prepare_application.py` prepares a tailored resume and cover letter from a job description. For a live application page, supply the user's existing Browser Use page/session to `JobPilot.prepare_and_autofill(...)`.
