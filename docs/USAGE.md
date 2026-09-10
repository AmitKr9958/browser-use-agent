# Browser Agent Usage

## 1. Sync the application layer

```powershell
git pull --ff-only origin main
```

## 2. Unit validation

```powershell
uv run pytest tests/test_tabs.py tests/test_connection.py tests/test_agent.py tests/test_cli.py -q
uv run ruff check browser_agent tests/test_tabs.py tests/test_connection.py tests/test_agent.py tests/test_cli.py
uv run pyright browser_agent
uv build
```

The unit suite does not open Chrome and does not call Gemini.

## 3. Real Chrome tab inspection

Start Browser Harness and make sure at least one Chrome tab is connected, then:

```powershell
uv run browser-harness --doctor
uv run python -m browser_agent.cli list
```

Expected behavior is a JSON array containing each connected tab's `index`, `target_id`, `title`, and `url`. An empty array means the Harness daemon is alive but no tab is currently exposed to this BrowserSession.

Example selection by title:

```powershell
uv run python -m browser_agent.cli select --title "GitHub"
```

Example selection by target ID:

```powershell
uv run python -m browser_agent.cli select --target-id "<target-id-from-list>"
```

The controller fails closed when a selector matches zero or multiple tabs.

## 4. Agent execution

`browser_agent.agents.run_on_tab()` requires a deterministic `TabSelector`, verifies the target before execution, and reconnects to Browser Harness after Browser Use completes to confirm the original target still exists. The default model is `gemini-3.6-flash`.

This local-first setup does not require Browser Use Cloud. Keep `BROWSER_USE_API_KEY` empty when using Gemini locally. Store the Google API key in `.env` and never commit it.
