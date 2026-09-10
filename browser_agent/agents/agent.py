"""Run Browser Use against a verified tab without consuming the Cloud browser credit."""

from __future__ import annotations

import inspect
from typing import Any

from browser_use import Agent, ChatGoogle

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.manager import TabManager, TabNotFoundError
from browser_agent.tabs.models import TabRecord, TabSelector


async def run_on_tab(
    task: str,
    selector: TabSelector,
    *,
    model: str = "gemini-3.6-flash",
    browser_session: Any | None = None,
) -> Any:
    """Select a target deterministically, run the agent, then verify the target still exists.

    Browser Use may reset/stop its BrowserSession when an Agent run completes. Therefore
    post-run verification intentionally creates a fresh Harness session when the caller
    supplied no session, rather than assuming the original session remains focused.
    """
    if not task.strip():
        raise ValueError("task must not be empty")

    session = browser_session or connect_browser_harness()
    manager = TabManager(session)
    selected: TabRecord = await manager.select_tab(selector)

    agent = Agent(
        task=task,
        llm=ChatGoogle(model=model),
        browser_session=session,
    )
    result = agent.run()
    history = await result if inspect.isawaitable(result) else result

    # Agent.run() can reset the session, clearing agent_focus_target_id. Reconnect to
    # the persistent Harness browser and verify the original target still exists.
    verification_session = connect_browser_harness()
    verification_manager = TabManager(verification_session)
    try:
        remaining = await verification_manager.list_tabs()
        if not any(tab.target_id == selected.target_id for tab in remaining):
            raise TabNotFoundError(
                f"Target tab disappeared during agent execution: {selected.target_id}"
            )
    finally:
        stop = getattr(verification_session, "stop", None)
        if callable(stop):
            cleanup_result = stop()
            if inspect.isawaitable(cleanup_result):
                await cleanup_result

    return history
