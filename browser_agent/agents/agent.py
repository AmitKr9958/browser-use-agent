"""Run Browser Use against a verified tab without consuming the Cloud browser credit."""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv
from browser_use import Agent, ChatGoogle, ChatOpenAI

from browser_agent.connection.harness import connect_browser_harness, stop_browser_harness_session
from browser_agent.models.india import DEFAULT_INDIA_RUNTIME, IndiaRuntimeConfig
from browser_agent.models.policy import DEFAULT_SENSITIVE_POLICY, SensitiveInteractionPolicy
from browser_agent.tabs.manager import TabManager, TabNotFoundError
from browser_agent.tabs.models import TabRecord, TabSelector
from browser_agent.utils import await_if_needed

logger = logging.getLogger(__name__)
load_dotenv()


def _build_task(task: str, india_runtime: IndiaRuntimeConfig | None, interaction_policy: SensitiveInteractionPolicy | None) -> str:
    sections: list[str] = []
    if india_runtime is not None:
        sections.append(india_runtime.instruction())
    if interaction_policy is not None:
        sections.append(interaction_policy.instruction())
    sections.append(f"Task:\n{task}" if sections else task)
    return "\n\n".join(sections)


def _build_fallback_llm(fallback_model: str | None) -> Any | None:
    model = (fallback_model or os.getenv("JOBPILOT_FALLBACK_MODEL", "")).strip()
    if not model or not os.getenv("OPENAI_API_KEY", "").strip():
        return None
    return ChatOpenAI(model=model)


def _build_primary_llm(model: str) -> Any:
    """Build the primary LLM, optionally routing through the local 9Router gateway."""
    router_key = os.getenv("NINEROUTER_API_KEY", "").strip()
    if router_key:
        base_url = os.getenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1").strip()
        router_model = os.getenv("NINEROUTER_MODEL", model).strip() or model
        return ChatOpenAI(base_url=base_url, model=router_model, api_key=router_key)
    return ChatGoogle(model=model)


async def _run_agent(agent_kwargs: dict[str, Any], max_steps: int) -> Any:
    agent = Agent(**agent_kwargs)
    return await await_if_needed(agent.run(max_steps=max_steps))


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
    """Select one tab, run the agent, verify the same target, and clean up owned sessions."""
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
    try:
        selected: TabRecord = await manager.select_tab(selector)
        effective_task = _build_task(task, india_runtime, interaction_policy)
        base_kwargs: dict[str, Any] = {
            "task": effective_task,
            "llm": _build_primary_llm(model),
            "browser_session": session,
            "use_judge": use_judge,
        }
        fallback_llm = _build_fallback_llm(fallback_model)
        if fallback_llm is not None:
            base_kwargs["fallback_llm"] = fallback_llm
        if available_file_paths:
            base_kwargs["available_file_paths"] = [str(path) for path in available_file_paths]
        if llm_timeout is not None:
            base_kwargs["llm_timeout"] = llm_timeout
        if step_timeout is not None:
            base_kwargs["step_timeout"] = step_timeout

        try:
            history = await _run_agent(base_kwargs, max_steps)
            logger.info("Primary agent completed on tab %s", selected.target_id)
        except Exception as primary_error:
            if fallback_llm is None:
                logger.error("Agent failed and no fallback LLM is configured", exc_info=True)
                raise
            logger.warning("Primary agent failed on tab %s; retrying with fallback: %s", selected.target_id, primary_error, exc_info=True)
            fallback_kwargs = dict(base_kwargs)
            fallback_kwargs["llm"] = fallback_llm
            fallback_kwargs.pop("fallback_llm", None)
            try:
                history = await _run_agent(fallback_kwargs, max_steps)
                logger.warning("Fallback agent succeeded on tab %s", selected.target_id)
            except Exception as fallback_error:
                logger.error("Both primary and fallback agents failed", exc_info=True)
                raise RuntimeError(
                    f"Agent execution failed. Primary: {primary_error}. Fallback: {fallback_error}"
                ) from fallback_error

        try:
            final_tab = await manager.verify_tab(selected)
            logger.info("Task completed and verified on tab %s (%s)", final_tab.target_id, final_tab.url)
        except TabNotFoundError as exc:
            raise TabNotFoundError(f"Target tab disappeared during agent execution: {selected.target_id}") from exc
        return history
    finally:
        if owns_session:
            try:
                await stop_browser_harness_session(session)
            except Exception as exc:
                logger.warning("Error stopping owned browser session: %s", exc, exc_info=True)
