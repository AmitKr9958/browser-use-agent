# Browser Agent Delivery Plan

This repository keeps the official Browser Use source intact and adds an application layer for deterministic local-browser automation.

## Phase 1 — Foundation
- Clone and retain the official Browser Use source.
- Keep `upstream` pointing at `browser-use/browser-use`.
- Keep secrets in `.env` only.
- Validate Python/uv, Browser Use import, and CLI installation.

## Phase 2 — Browser Harness integration
- Attach to the existing Chrome instance through Browser Harness.
- Discover the CDP WebSocket dynamically with `get_ws_url()`.
- Avoid hard-coded Chrome session UUIDs.
- Use Gemini 3.6 Flash without consuming Browser Use Cloud credit.

## Phase 3 — Deterministic multi-tab control
- Enumerate tabs as stable records containing index, target ID, title, and URL.
- Locate by target ID, exact title/URL, or case-insensitive contains matching.
- Reject ambiguous matches rather than guessing.
- Select through Browser Use's `switch_to_tab()`.

## Phase 4 — Verified agent execution
- Require a tab selector before agent execution.
- Verify the Browser Use agent focus target after switching.
- Re-verify target identity after execution.
- Keep URL/title as metadata only because navigation can legitimately change them.

## Phase 5 — Production hardening
- Add unit tests for connection, selection, ambiguity, missing targets, and agent orchestration.
- Add a CLI for tab inspection/selection.
- Add GitHub Actions unit-test CI with no browser or API key requirement.
- Keep cloud authentication optional and local-first.

## Exit criteria
Phase 5 is complete when the unit suite passes, CI is green, and the local integration smoke test can list and select the user's real Browser Harness tabs without opening a second Chrome instance.
