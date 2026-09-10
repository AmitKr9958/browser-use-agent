"""Production-oriented CLI for Browser Harness tab control and agent execution."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from typing import Any

from dotenv import load_dotenv

from browser_agent.agents.agent import run_on_tab
from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.manager import TabManager
from browser_agent.tabs.models import TabSelector


def _add_selector_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--index", type=int)
    group.add_argument("--target-id")
    group.add_argument("--title")
    group.add_argument("--url")
    group.add_argument("--title-contains")
    group.add_argument("--url-contains")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic Browser Harness automation")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all open browser tabs")

    select = sub.add_parser("select", help="Select and verify exactly one tab")
    _add_selector_arguments(select)

    run = sub.add_parser("run", help="Run a Browser Use task on exactly one selected tab")
    run.add_argument("--task", required=True, help="Task for the Browser Use agent")
    _add_selector_arguments(run)
    run.add_argument("--model", default="gemini-3.6-flash")
    run.add_argument("--max-steps", type=int, default=100)
    run.add_argument("--llm-timeout", type=int, default=None)
    run.add_argument("--step-timeout", type=int, default=None)
    return parser


def selector_from_args(args: argparse.Namespace) -> TabSelector:
    values = {
        "index": args.index,
        "target_id": args.target_id,
        "title": args.title,
        "url": args.url,
        "title_contains": args.title_contains,
        "url_contains": args.url_contains,
    }
    return TabSelector(**{key: value for key, value in values.items() if value is not None})


def _history_result(history: Any) -> str | None:
    final_result = getattr(history, "final_result", None)
    if callable(final_result):
        result = final_result()
        return None if result is None else str(result)
    return None if history is None else str(history)


async def main_async(args: argparse.Namespace) -> int:
    load_dotenv()

    if args.command == "run":
        history = await run_on_tab(
            args.task,
            selector_from_args(args),
            model=args.model,
            max_steps=args.max_steps,
            llm_timeout=args.llm_timeout,
            step_timeout=args.step_timeout,
        )
        result = _history_result(history)
        print(json.dumps({"success": True, "result": result}, indent=2))
        return 0

    manager = TabManager(connect_browser_harness())
    if args.command == "list":
        print(json.dumps([asdict(tab) for tab in await manager.list_tabs()], indent=2))
        return 0

    selected = await manager.select_tab(selector_from_args(args))
    print(json.dumps(asdict(selected), indent=2))
    return 0


def main() -> None:
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(main_async(args)))
    except (RuntimeError, LookupError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
