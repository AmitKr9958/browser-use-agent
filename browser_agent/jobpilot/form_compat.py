"""Site-independent heuristics for robust career-application form handling.

The browser agent remains responsible for actual DOM interaction. This module keeps
field classification, sensitive-data detection, submission detection, and common ATS
family hints deterministic so prompts and tests do not depend on one vendor's markup.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

FINAL_SUBMISSION_RE = re.compile(
    r"\b(?:submit(?:\s+application)?|apply(?:\s+now)?|send\s+application|complete\s+application|finish\s+application|finalize\s+application|send)\b",
    re.I,
)

SENSITIVE_RE = re.compile(
    r"\b(?:aadhaar|aadhar|pan\s*(?:card|number)?|passport|driving\s*licen[cs]e|social\s+security|ssn|tax\s*(?:id|identification)|national\s+id|government\s+id|identity\s+(?:number|document)|bank\s+(?:account|details)|routing\s+number|credit\s+card|debit\s+card|otp|one[-\s]?time\s+password|password|mfa|multi[-\s]?factor|captcha|salary|compensation|notice\s+period|date\s+of\s+birth|dob|gender|race|ethnicity|disability|veteran|criminal|sponsorship|work\s+authorization|legally\s+authorized|consent|background\s+check)\b",
    re.I,
)

# Ordered from specific to broad. A field such as "State" is intentionally
# represented by the generic location class; downstream code must use the
# accessible question/value rather than assuming one physical address field.
FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "name": ("full name", "first name", "last name", "given name", "family name", "legal name", "preferred name"),
    "email": ("email", "e-mail"),
    "phone": ("phone", "mobile", "telephone", "contact number"),
    "location": ("address line 1", "address line 2", "street address", "city", "location", "address", "state", "province", "country", "postal", "zip", "pincode"),
    "linkedin": ("linkedin",),
    "portfolio": ("portfolio", "personal website", "website", "github profile"),
    "resume": ("resume", "cv", "curriculum vitae", "upload resume", "upload cv"),
    "cover_letter": ("cover letter", "covering letter", "motivation", "supporting statement"),
    "work_authorization": ("authorized to work", "work authorization", "right to work"),
    "sponsorship": ("sponsorship", "sponsor", "visa"),
    "salary": ("salary", "compensation", "expected pay", "pay expectation"),
}

ATS_FAMILIES: dict[str, tuple[str, ...]] = {
    "greenhouse": ("greenhouse.io",),
    "lever": ("jobs.lever.co", "lever.co"),
    "workday": ("myworkdayjobs.com", "workday.com"),
    "smartrecruiters": ("smartrecruiters.com",),
    "icims": ("icims.com", "icims.jobs"),
    "workable": ("apply.workable.com", "workable.com"),
    "ashby": ("ashbyhq.com", "jobs.ashbyhq.com"),
    "successfactors": ("successfactors.com",),
    "taleo": ("taleo.net",),
    "oracle": ("oraclecloud.com", "oracle.com"),
    "sap": ("jobs.sap.com", "successfactors.com"),
    "indeed": ("indeed.com",),
    "linkedin": ("linkedin.com",),
}


def normalize_label(value: str) -> str:
    """Normalize visible labels/placeholders before classification."""
    return " ".join(value.casefold().replace("_", " ").replace("-", " ").split())


def classify_field(label: str) -> str | None:
    """Return the safest known field class for a visible field label."""
    normalized = normalize_label(label)
    for field, patterns in FIELD_PATTERNS.items():
        if any(pattern in normalized for pattern in patterns):
            return field
    return None


def is_sensitive_field(label: str) -> bool:
    """Return True when the field must not be guessed or filled without explicit data."""
    return bool(SENSITIVE_RE.search(normalize_label(label)))


def is_final_submission_control(label: str) -> bool:
    """Return True for controls that can finalize an application."""
    return bool(FINAL_SUBMISSION_RE.search(normalize_label(label)))


def detect_ats_family(url: str) -> str:
    """Identify a known career platform from the hostname without assuming selectors."""
    host = urlparse(url).hostname or ""
    host = host.casefold().rstrip(".")
    for family, domains in ATS_FAMILIES.items():
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            return family
    return "generic"


def build_universal_form_policy(url: str) -> str:
    """Return a deterministic policy for the browser agent across career platforms."""
    family = detect_ats_family(url)
    return f"""
UNIVERSAL CAREER-FORM POLICY
Detected career platform family: {family}

FIELD DISCOVERY
- Inspect the complete accessible form, not only the first viewport.
- Use visible label text, associated labels, aria-label, placeholder, name, autocomplete, input type, and surrounding question text to identify fields.
- Re-scan after every safe Next/Continue/Save-and-Continue step because multi-page forms frequently replace the DOM.
- Inspect supported same-origin/cross-origin frames and shadow-root content exposed by the browser automation layer.
- Prefer accessible names and real user interaction over brittle CSS/XPath selectors.
- Do not assume field order, element IDs, class names, or vendor-specific selectors.

FIELD HANDLING
- Map name/email/phone/location/LinkedIn/portfolio/resume/cover-letter fields to explicit supplied values only.
- For native select, custom combobox, autocomplete, radio groups, checkboxes, date controls, file uploads, and rich-text editors, interact through the visible control and verify the resulting value/state.
- Preserve any non-empty field unless replacing it is explicitly required and the replacement value is supplied.
- Treat existing non-empty values as authoritative page state; record conflicts instead of silently overwriting them.
- For resume upload, verify the selected filename or attached-file state before progressing.
- For cover-letter fields, use the supplied generated cover letter only; never invent missing personal facts.
- If a field cannot be mapped confidently, leave it unchanged and report it.

SENSITIVE / MANUAL REVIEW
- Never guess or infer government IDs, passport/Aadhaar/PAN, bank/payment data, passwords, OTP/MFA, CAPTCHA, compensation, notice period, demographic/EEO, criminal-history, consent/legal attestations, sponsorship, or work-authorization answers.
- Fill sponsorship/work authorization only when the exact value is explicitly supplied and the question is unambiguous.
- Stop for login, CAPTCHA, MFA/OTP, payment, identity verification, or any other security challenge.

NAVIGATION
- Safe navigation controls may include Next, Continue, Save, Save and Continue, or similar controls when they are clearly non-final.
- Before clicking a navigation control, verify it is not a final-submission control and that no unresolved mandatory sensitive/unknown question is being bypassed.
- Never click a control classified as final submission, including Submit Application, Apply, Send Application, Complete Application, Finish Application, Finalize, or equivalent wording.
- If the page reaches final review/confirmation, stop and return a field-by-field verification report.

VERIFICATION
- After every field interaction, verify the visible value/state when possible.
- Re-read the complete page after dynamic updates and before each safe navigation step.
- Before stopping, report: page/step, filled fields, verified fields, skipped fields with reasons, conflicts, upload status, blockers, and whether a final submission control remains untouched.
- Never claim completion solely because an agent action was attempted; completion requires observed verification evidence.
""".strip()
