"""Run Browser Use against a verified tab without consuming the Cloud browser credit."""

from __future__ import annotations

import inspect
from typing import Any, cast

from browser_use import Agent, ChatGoogle

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.manager import TabManager, TabNotFoundError
from browser_agent.tabs.models import TabRecord, TabSelector


async def _await_if_needed(value: Any) -> Any:
    """Await a result when it is awaitable; otherwise return it unchanged."""
    if inspect.isawaitable(value):
        return await value
    return value


async def run_on_tab(
    task: str,
    selector: TabSelector,
    *,
    model: str = 'gemini-3.6-flash',
    browser_session: Any | None = None,
    max_steps: int = 100,
    llm_timeout: int | None = None,
    step_timeout: int | None = None,
) -> Any:
    """Select a target deterministically, run the agent, then verify the target still exists.

    ``max_steps`` and timeout overrides make live runs bounded and testable without
    changing the normal Browser Use defaults when no overrides are supplied.
    """
    if not task.strip():
        raise ValueError('task must not be empty')
    if max_steps < 1:
        raise ValueError('max_steps must be at least 1')
    if llm_timeout is not None and llm_timeout < 1:
        raise ValueError('llm_timeout must be at least 1 second')
    if step_timeout is not None and step_timeout < 1:
        raise ValueError('step_timeout must be at least 1 second')

    session = browser_session or connect_browser_harness()
    manager = TabManager(session)
    selected: TabRecord = await manager.select_tab(selector)

    agent_kwargs: dict[str, Any] = {
        'task': task,
        'llm': ChatGoogle(model=model),
        'browser_session': session,
    }
    if llm_timeout is not None:
        agent_kwargs['llm_timeout'] = llm_timeout
    if step_timeout is not None:
        agent_kwargs['step_timeout'] = step_timeout

    agent = Agent(**agent_kwargs)
    history = await _await_if_needed(cast(Any, agent.run(max_steps=max_steps)))

    # Agent.run() can reset the session, so reconnect to the persistent Harness browser
    # and verify that the original target still exists after execution.
    verification_session = connect_browser_harness()
    verification_manager = TabManager(verification_session)
    try:
        remaining = await verification_manager.list_tabs()
        if not any(tab.target_id == selected.target_id for tab in remaining):
            raise TabNotFoundError(
                f'Target tab disappeared during agent execution: {selected.target_id}'
            )
    finally:
        stop = getattr(verification_session, 'stop', None)
        if callable(stop):
            await _await_if_needed(cast(Any, stop()))

    return history
