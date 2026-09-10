# Browser Agent Usage

## 1. Sync the application layer

```powershell
git pull --ff-only origin main
```

## 2. Unit and package validation

```powershell
uv run pytest tests/test_tabs.py tests/test_connection.py tests/test_agent.py tests/test_cli.py -q
uv run ruff check browser_agent tests/test_tabs.py tests/test_connection.py tests/test_agent.py tests/test_cli.py examples/live_harness_agent_smoke.py
uv run pyright browser_agent
uv build
```

The application-layer unit suite does not open Chrome and does not call Gemini.

## 3. Real Chrome tab inspection

Start Browser Harness and make sure at least one Chrome tab is connected, then:

```powershell
uv run browser-harness --doctor
uv run python -m browser_agent.cli list
```

Expected behavior is a JSON array containing each connected tab's `index`, `target_id`, `title`, and `url`.

## 4. Deterministic selection

Select by exact title:

```powershell
uv run python -m browser_agent.cli select --title "GitHub"
```

Select by stable target ID:

```powershell
uv run python -m browser_agent.cli select --target-id "<target-id-from-list>"
```

The controller fails closed when a selector matches zero or multiple tabs.

## 5. Run an agent on an existing tab

The production CLI can execute a task against one verified Harness tab:

```powershell
uv run browser-agent run --title-contains "9Router" --task "Read the current page title and return it. Do not navigate, click, type, or modify anything." --max-steps 5 --llm-timeout 60 --step-timeout 60
```

The command returns JSON with `success` and the agent's final result. The default model is `gemini-3.6-flash`; override it with `--model` when another directly configured provider is available.

`run` requires exactly one tab selector and verifies stable target identity before execution. After Browser Use completes, the application reconnects to Browser Harness and confirms the original target still exists.

## 6. Local-first configuration

This project does not require Browser Use Cloud for the local Harness + Gemini flow. Keep `BROWSER_USE_API_KEY` empty when using Gemini directly, set `GOOGLE_API_KEY` in `.env`, and never commit `.env`.

The Browser Harness daemon and the operator's Chrome process are external runtime dependencies. Cloud authentication may be reported as optional by `browser-harness doctor`; that does not block the local flow.
