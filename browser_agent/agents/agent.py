"""Run Browser Use against a verified tab without consuming the Cloud browser credit."""

from __future__ import annotations

import inspect
import os
from typing import Any, cast

from dotenv import load_dotenv
from browser_use import Agent, ChatGoogle, ChatOpenAI

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.models.india import DEFAULT_INDIA_RUNTIME, IndiaRuntimeConfig
from browser_agent.models.policy import DEFAULT_SENSITIVE_POLICY, SensitiveInteractionPolicy
from browser_agent.tabs.manager import TabManager, TabNotFoundError
from browser_agent.tabs.models import TabRecord, TabSelector

# Load local development/runtime configuration without overriding explicitly supplied
# process environment variables. The .env file itself is ignored by Git.
load_dotenv()


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


def _build_task(
    task: str,
    india_runtime: IndiaRuntimeConfig | None,
    interaction_policy: SensitiveInteractionPolicy | None,
) -> str:
    """Build the model instruction without altering the caller's task semantics."""
    sections: list[str] = []
    if india_runtime is not None:
        sections.append(india_runtime.instruction())
    if interaction_policy is not None:
        sections.append(interaction_policy.instruction())
    sections.append(f"Task:\n{task}" if sections else task)
    return "\n\n".join(sections)


def _build_fallback_llm(fallback_model: str | None) -> Any | None:
    """Build an optional OpenAI fallback when explicitly configured and authenticated."""
    model = (fallback_model or os.getenv("JOBPILOT_FALLBACK_MODEL", "")).strip()
    if not model or not os.getenv("OPENAI_API_KEY"):
        return None
    return ChatOpenAI(model=model)


def _build_primary_llm(model: str) -> Any:
    """Build the primary LLM, optionally routing through a local 9Router gateway.

    When NINEROUTER_API_KEY is configured, JobPilot uses the OpenAI-compatible
    9Router endpoint instead of calling Gemini directly. This keeps the credential
    outside source control and lets 9Router handle provider routing/fallback.
    """
    router_key = os.getenv("NINEROUTER_API_KEY", "").strip()
    if router_key:
        base_url = os.getenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1").strip()
        router_model = os.getenv("NINEROUTER_MODEL", model).strip() or model
        return ChatOpenAI(base_url=base_url, model=router_model, api_key=router_key)
    return ChatGoogle(model=model)


async def run_on_tab(
    task: str,
    selector: TabSelector,
    *,
    model: str = "gemini-3.6-flash",
    browser_session: Any | None = None,
    max_steps: int = 100,
    llm_timeout: int | None = None,
    step_timeout: int | None = None,
    fallback_model: str | None = None,
    available_file_paths: list[str] | None = None,
    use_judge: bool = False,
    india_runtime: IndiaRuntimeConfig | None = DEFAULT_INDIA_RUNTIME,
    interaction_policy: SensitiveInteractionPolicy | None = DEFAULT_SENSITIVE_POLICY,
) -> Any:
    """Select one tab, run the agent, verify the target, and clean up owned sessions.

    Indian regional conventions and conservative sensitive-interaction boundaries are
    enabled by default. Pass either option as ``None`` to disable that guidance.

    ``available_file_paths`` explicitly grants Browser Use access to local files that
    the task is allowed to upload. ``fallback_model`` enables an OpenAI fallback only
    when an ``OPENAI_API_KEY`` is present. If ``NINEROUTER_API_KEY`` is set, the
    primary model is routed through the OpenAI-compatible 9Router gateway instead.
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
    effective_task = _build_task(task, india_runtime, interaction_policy)

    agent_kwargs: dict[str, Any] = {
        "task": effective_task,
        "llm": _build_primary_llm(model),
        "browser_session": session,
        "use_judge": use_judge,
    }
    fallback_llm = _build_fallback_llm(fallback_model)
    if fallback_llm is not None:
        agent_kwargs["fallback_llm"] = fallback_llm
    if available_file_paths:
        agent_kwargs["available_file_paths"] = [str(path) for path in available_file_paths]
    if llm_timeout is not None:
        agent_kwargs["llm_timeout"] = llm_timeout
    if step_timeout is not None:
        agent_kwargs["step_timeout"] = step_timeout

    try:
        agent = Agent(**agent_kwargs)
        history = await _await_if_needed(cast(Any, agent.run(max_steps=max_steps)))

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
        if owns_session:
            await _best_effort_stop(session)
