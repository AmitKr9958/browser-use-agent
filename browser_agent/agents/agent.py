"""Run Browser Use against a verified tab."""

from __future__ import annotations

from typing import Any

from browser_use import Agent, ChatGoogle

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.manager import TabManager
from browser_agent.tabs.models import TabRecord, TabSelector


async def run_on_tab(
    task: str,
    selector: TabSelector,
    *,
    model: str = "gemini-3.6-flash",
    browser_session: Any | None = None,
) -> Any:
    """Select and verify a tab before allowing Browser Use to execute a task."""
    session = browser_session or connect_browser_harness()
    manager = TabManager(session)
    selected: TabRecord = await manager.select_tab(selector)

    agent = Agent(
        task=task,
        llm=ChatGoogle(model=model),
        browser_session=session,
    )
    history = await agent.run()

    # Re-verify after execution so callers know which tab the agent ended on.
    await manager.verify_tab(selected)
    return history
