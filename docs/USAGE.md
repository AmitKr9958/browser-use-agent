# Browser Agent Usage

## 1. Sync the application layer

```powershell
git pull --ff-only origin main
```

## 2. Unit validation

```powershell
uv run pytest tests/test_tabs.py tests/test_connection.py tests/test_agent.py -q
```

The unit suite does not open Chrome and does not call Gemini.

## 3. Real Chrome tab inspection

Start Browser Harness and make sure at least one Chrome tab is connected, then:

```powershell
uv run python -m browser_agent.cli list
```

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

`browser_agent.agents.run_on_tab()` requires a deterministic `TabSelector` and verifies the Browser Use focus target before execution. The default model is `gemini-3.6-flash`.

Keep `BROWSER_USE_API_KEY` empty for this local-first setup. A Google API key is read from `.env` and must never be committed.
