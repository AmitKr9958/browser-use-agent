"""Run Browser Use against a verified tab without consuming the Cloud browser credit."""

from __future__ import annotations

import inspect
from typing import Any, cast

from browser_use import Agent, ChatGoogle

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.models.india import DEFAULT_INDIA_RUNTIME, IndiaRuntimeConfig
from browser_agent.tabs.manager import TabManager, TabNotFoundError
from browser_agent.tabs.models import TabRecord, TabSelector


async def _await_if_needed(value: Any) -> Any:
    """Await a result when it is awaitable; otherwise return it unchanged."""
    if inspect.isawaitable(value):
        return await value

    return value


async def _best_effort_stop(session: Any) -> None:
    """Stop a BrowserSession and wait for its shutdown coroutine when supported."""
    stop = getattr(session, "stop", None)
    if callable(stop):
        await _await_if_needed(cast(Any, stop)())


async def run_on_tab(
    task: str,
    selector: TabSelector,
    *,
    model: str = "gemini-3.6-flash",
    browser_session: Any | None = None,
    max_steps: int = 100,
    llm_timeout: int | None = None,
    step_timeout: int | None = None,
    india_runtime: IndiaRuntimeConfig | None = DEFAULT_INDIA_RUNTIME,
) -> Any:
    """Select one tab, run the agent, verify the target, and clean up owned sessions.

    Indian regional conventions are included by default. Pass ``india_runtime=None``
    when a task must use no regional guidance.
    """
    if not task.strip():
        raise ValueError("task must not be empty")
    if max_steps < 1:
        raise ValueError("max_steps must be at least 1")
    if llm_timeout is not None and llm_timeout < 1:
        raise ValueError("llm_timeout must be at least 1 second")
    if step_timeout is not None and step_timeout < 1:
        raise ValueError("step_timeout must be at least 1 second")

    owns_session = browser_session is None
    session = browser_session or connect_browser_harness()
    manager = TabManager(session)
    selected: TabRecord = await manager.select_tab(selector)

    effective_task = task
    if india_runtime is not None:
        effective_task = f"{india_runtime.instruction()}\n\nTask:\n{task}"

    agent_kwargs: dict[str, Any] = {
        "task": effective_task,
        "llm": ChatGoogle(model=model),
        "browser_session": session,
    }
    if llm_timeout is not None:
        agent_kwargs["llm_timeout"] = llm_timeout
    if step_timeout is not None:
        agent_kwargs["step_timeout"] = step_timeout

    try:
        agent = Agent(**agent_kwargs)
        history = await _await_if_needed(cast(Any, agent.run(max_steps=max_steps)))

        # Agent.run() can reset the session, so reconnect to the persistent Harness browser
        # and verify that the original target still exists after execution.
        verification_session = connect_browser_harness()
        try:
            verification_manager = TabManager(verification_session)
            remaining = await verification_manager.list_tabs()
            if not any(tab.target_id == selected.target_id for tab in remaining):
                raise TabNotFoundError(
                    f"Target tab disappeared during agent execution: {selected.target_id}"
                )
        finally:
            await _best_effort_stop(verification_session)

        return history
    finally:
        # An internally-created session must be explicitly stopped so Browser Use's
        # reconnect/watchdog tasks cannot survive the CLI event loop. keep_alive=True
        # on the Harness profile keeps the external Chrome browser alive.
        if owns_session:
            await _best_effort_stop(session)
