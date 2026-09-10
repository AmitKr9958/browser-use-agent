# Browser Agent Architecture

## Scope

This repository uses the official Browser Use implementation as the browser-agent engine and adds a thin application layer under `browser_agent/`. The application layer is intentionally isolated so upstream Browser Use updates can be pulled without rewriting its core.

## Runtime flow

```text
User task
   |
   v
Browser Harness Chrome
   |
   | dynamic CDP WebSocket (`get_ws_url()`)
   v
BrowserSession
   |
   v
TabManager
   |-- list_tabs()
   |-- find_tab()
   |-- select_tab()
   `-- verify_tab()
   |
   v
Browser Use Agent + Gemini 3.6 Flash
   |
   v
Post-run target existence verification
```

## Safety invariants

1. No hard-coded Chrome CDP session UUIDs.
2. A tab selector must identify exactly one tab.
3. Ambiguous and missing selectors fail closed.
4. The selected target ID is verified before the agent starts.
5. Agent completion does not assume the original BrowserSession remains alive; Browser Use may reset it.
6. Post-run verification reconnects to Browser Harness and confirms the original target still exists.
7. Browser Use Cloud credentials are not required for the local flow.
8. Secrets belong in `.env`, which must remain untracked.

## Operational boundaries

The local Chrome process and Browser Harness daemon are external runtime dependencies. Unit tests deliberately mock those dependencies. The real-browser smoke test is therefore an acceptance test that must be executed on the operator's Windows machine with Browser Harness connected to Chrome.

## Upstream strategy

The official Browser Use repository remains the upstream source. Application code belongs under `browser_agent/`, tests for this layer belong in the dedicated `tests/test_*.py` files, and changes to Browser Use internals should be avoided unless an upstream defect requires them.
