# Production Readiness — Browser Agent + Job Application Layer

**Repository:** `AmitKr9958/browser-use-agent`  
**Branch:** `main`  
**Last validation:** September 15, 2026  
**Current status:** **VALIDATED FOR MANUAL TESTING — NOT YET DECLARED PRODUCTION-READY**

## Why this is not yet marked production-ready

The repository's automated CI gates now pass, including unit tests, the safe live web reachability smoke test, Ruff, Pyright, build, and package-content verification.

The live CI test is intentionally limited: it verifies that the public dummy application page is reachable and contains the expected safety/task markers. It does **not** execute a real BrowserSession + LLM autofill against that page. A local Browser Use session has previously been connected successfully and the dummy form's fields/file input/final Submit control were inspected, but an end-to-end agent-driven upload-and-verification run has not been validated as part of this final CI cycle. Therefore the full application workflow remains **UNVERIFIED** until that safe manual smoke test is completed.

The project must not be called production-ready until that workflow is validated without submitting the dummy application.

## Automated validation

GitHub Actions run **#340** (`34962807752`) for commit `f8d14cee1aa024a076696a2f32e5599b336384e7` completed successfully.

| Gate | Result |
|---|---|
| `uv sync --dev` | PASS |
| Browser-agent + JobPilot unit tests | PASS — **97 passed** |
| Public dummy web smoke tests | PASS — **2 passed** |
| Ruff | PASS — 0 remaining errors |
| Pyright | PASS — **0 errors, 0 warnings** |
| `uv build` | PASS — sdist + wheel created |
| Package verification | PASS — required JobPilot/session modules present |
| CI job | **PASS** |

The CI workflow also exercises the browser-agent and JobPilot test modules without requiring personal credentials.

## Important implementation fixes

### Browser session lifecycle

The application now distinguishes internally-owned browser sessions from caller-supplied sessions. Internally-created sessions are cleaned up; supplied sessions are not incorrectly closed by the callee. Browser startup is explicit where required, and cleanup is attempted after normal execution and exceptions.

### Tab and target safety

Tab selection requires deterministic selectors, rejects ambiguous matches, tracks target identity, and verifies the selected target and page metadata after switching. The Browser Use event-bus boundary is explicitly typed with a small protocol rather than weakening Pyright globally.

### Agent fallback

The agent supports a primary LLM plus an optional fallback model and retries on the same browser session. Primary/fallback failures are logged, and the final tab is verified after execution.

### Job application safety

The application task explicitly forbids final submission and requires stopping at CAPTCHA, OTP/MFA, login, payment, identity verification, or other high-risk steps. It requires live read-back verification for fields and file uploads, preserves conflicting non-empty values, and reports ambiguous or unsupported questions for manual review.

Application reports reject `submitted=true` and do not treat generic natural-language claims as proof of completion. Planned resume/file uploads must be explicitly verified before a structured result can be considered completed.

### 9Router configuration

The primary model can use an OpenAI-compatible 9Router endpoint through environment variables:

```text
BROWSER_AGENT_ROUTER_API_KEY=...
BROWSER_AGENT_ROUTER_BASE_URL=http://localhost:20128/v1
BROWSER_AGENT_ROUTER_MODEL=kr/claude-sonnet-4.5
```

Legacy `NINEROUTER_*` aliases are retained for compatibility. Credentials are not stored in source control; `.env` is ignored and `.env.example` contains only placeholders.

### India runtime

The default runtime is configurable and currently defaults to:

- Locale: `en-IN`
- Timezone: `Asia/Kolkata`
- Currency: `INR`
- Country: `IN`

These are configuration defaults, not vendor-specific website assumptions.

## Known validation boundary

The following items are implemented and covered by automated tests, but some require a real user-controlled browser/application to be considered fully operational:

- end-to-end BrowserSession + LLM autofill
- real resume upload into the dummy form and browser-side upload verification
- generated cover-letter insertion into a live application field
- behavior across arbitrary third-party career-site implementations
- CAPTCHA/login/OTP/MFA/manual-review handoff in a real blocked flow

No real job application should be submitted during validation.

## Manual smoke-test handoff

1. Start 9Router and confirm the selected model is available.
2. Put the 9Router credential only in local `.env`; never paste or commit it.
3. Start/connect Browser Use/Browser Harness.
4. Use the public dummy application URL configured by the repository's live-test documentation.
5. Supply a real resume path through the CLI/configuration; do not hardcode the path in source code.
6. Run the JobPilot prepare/apply workflow.
7. Verify the job description, profile, tailored resume, cover letter, form fields, and required-field detection.
8. Verify the resume file input visibly reports the selected/attached filename when upload is supported.
9. Verify every reported filled field is read back from the live page.
10. Verify ambiguous/sensitive/missing fields remain unchanged and are reported.
11. Verify the agent stops before the final Submit/Apply/Send/Complete control.
12. Review the final state manually. Only the user may submit.

### Failure conditions

Treat the run as **blocked/failed/incomplete**, not successful, if:

- the browser disconnects;
- the target/tab changes unexpectedly;
- a required field cannot be answered from supplied evidence;
- a resume upload is skipped or cannot be verified;
- a cover-letter insertion cannot be verified;
- a CAPTCHA, OTP, MFA, login, payment, or identity-verification step appears;
- the agent claims submission;
- the final submission control cannot be safely left untouched; or
- the application result contains no explicit browser-side verification.

## Security note

Any API credential previously exposed outside the local secret store should be considered compromised and rotated/revoked before production use. Do not reuse an exposed credential merely because it is absent from the repository.

## Release decision

**Current decision: NOT YET PRODUCTION-READY.**

Automated repository gates are green. The remaining gate is a safe, end-to-end manual Browser Use application smoke test covering actual field interaction, resume upload verification, cover-letter handling, blockers, and the mandatory pre-submit stop. Once that is successfully demonstrated, this document can be updated with the exact evidence and release decision.
