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
- Switch through Browser Use's public event-bus tab-switch API when a switch is required.
- Avoid redundant switches when the requested target is already active.

## Phase 4 — Verified agent execution
- Require a tab selector before agent execution.
- Verify the selected target before the agent starts.
- Run the Browser Use agent with configurable step and timeout limits.
- Reconnect to Browser Harness after execution because Browser Use may reset its session.
- Re-verify that the original stable target ID still exists after execution.
- Keep URL/title as metadata only because navigation can legitimately change them.

## Phase 5 — Production hardening
- Unit-test connection, selection, ambiguity, missing targets, and agent orchestration.
- Provide a CLI for tab inspection, deterministic selection, and agent execution.
- Add GitHub Actions CI for tests, lint, type checking, and package verification.
- Keep cloud authentication optional and local-first.
- Keep the upstream Browser Use implementation isolated from application-layer changes.
- Document the exact local operational flow and safety invariants.

## Exit criteria
The current production baseline is complete when the unit suite passes, CI is green, and the local integration smoke test can run a bounded Browser Use task against a real Browser Harness tab without opening a second Chrome instance.

## Next extension points
The application layer is intentionally ready for higher-level capabilities such as task templates, structured results, additional model providers, and richer tab-selection policies without modifying Browser Use internals.
