"""Small production-oriented CLI for inspecting and selecting browser tabs."""

from __future__ import annotations

import argparse
import asyncio
import json

from dotenv import load_dotenv

from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.manager import TabManager
from browser_agent.tabs.models import TabSelector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic Browser Harness tab controller")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List all open browser tabs")

    select = sub.add_parser("select", help="Select and verify exactly one tab")
    group = select.add_mutually_exclusive_group(required=True)
    group.add_argument("--index", type=int)
    group.add_argument("--target-id")
    group.add_argument("--title")
    group.add_argument("--url")
    group.add_argument("--title-contains")
    group.add_argument("--url-contains")
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


async def main_async(args: argparse.Namespace) -> int:
    load_dotenv()
    manager = TabManager(connect_browser_harness())
    if args.command == "list":
        print(json.dumps([tab.__dict__ for tab in await manager.list_tabs()], indent=2))
        return 0

    selected = await manager.select_tab(selector_from_args(args))
    print(json.dumps(selected.__dict__, indent=2))
    return 0


def main() -> None:
    args = build_parser().parse_args()
    try:
        raise SystemExit(asyncio.run(main_async(args)))
    except (RuntimeError, LookupError, ValueError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    main()
