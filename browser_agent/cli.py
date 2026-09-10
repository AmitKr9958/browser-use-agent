"""Production CLI for AI agent tasks and deterministic one-off browser actions."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from typing import Any

from dotenv import load_dotenv

from browser_agent.actions.basic import click_selector, open_url, screenshot
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
    parser = argparse.ArgumentParser(description="Browser Use AI automation and deterministic browser actions")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all open browser tabs")

    select = sub.add_parser("select", help="Select and verify exactly one tab")
    _add_selector_arguments(select)

    run = sub.add_parser("run", help="Run an AI Browser Use task on exactly one selected tab")
    run.add_argument("--task", required=True, help="High-level task for the Browser Use agent")
    _add_selector_arguments(run)
    run.add_argument("--model", default="gemini-3.6-flash")
    run.add_argument("--max-steps", type=int, default=100)
    run.add_argument("--llm-timeout", type=int, default=None)
    run.add_argument("--step-timeout", type=int, default=None)

    open_command = sub.add_parser("open", help="Open a URL in a new browser tab")
    open_command.add_argument("url", help="URL to open")

    click_command = sub.add_parser("click", help="Click exactly one element on the current page")
    click_command.add_argument("--selector", required=True, help="CSS selector that must match exactly one element")

    screenshot_command = sub.add_parser("screenshot", help="Save a PNG screenshot of the current page")
    screenshot_command.add_argument("output", help="Output PNG path")
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
        print(json.dumps({"success": True, "result": _history_result(history)}, indent=2))
        return 0

    session = connect_browser_harness()
    if args.command == "open":
        print(json.dumps({"success": True, **await open_url(args.url, session)}, indent=2))
        return 0
    if args.command == "click":
        print(json.dumps({"success": True, **await click_selector(args.selector, browser_session=session)}, indent=2))
        return 0
    if args.command == "screenshot":
        path = await screenshot(args.output, browser_session=session)
        print(json.dumps({"success": True, "path": str(path)}, indent=2))
        return 0

    manager = TabManager(session)
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
