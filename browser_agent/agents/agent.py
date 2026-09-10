"""Run Browser Use against a verified tab without consuming the Cloud browser credit."""

from __future__ import annotations

from typing import Any, Awaitable, cast

from browser_use import Agent, ChatGoogle

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.manager import TabManager, TabNotFoundError
from browser_agent.tabs.models import TabRecord, TabSelector


async def _await_if_needed(value: Any) -> Any:
    """Await an Agent result when async; otherwise return the synchronous result."""
    if isinstance(value, Awaitable):
        return await value
    return value


async def run_on_tab(
    task: str,
    selector: TabSelector,
    *,
    model: str = "gemini-3.6-flash",
    browser_session: Any | None = None,
) -> Any:
    """Select a target deterministically, run the agent, then verify the target still exists."""
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
    result = cast(Any, agent.run())
    history = await _await_if_needed(result)

    # Agent.run() can reset the session, so reconnect to the persistent Harness browser
    # and verify that the original target still exists after execution.
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
            await _await_if_needed(cast(Any, stop()))

    return history
