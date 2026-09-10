"""Bounded live smoke test for Browser Harness + Browser Use + Gemini."""

from __future__ import annotations

import argparse
import asyncio

from dotenv import load_dotenv

from browser_agent.agents.agent import run_on_tab
from browser_agent.connection.harness import connect_browser_harness
from browser_agent.tabs.models import TabSelector


async def main(title_contains: str) -> None:
    """Run one bounded read-only task against an existing Harness tab."""
    load_dotenv()
    session = connect_browser_harness()
    history = await run_on_tab(
        "Read the current page title and return it. Do not navigate, click, type, or modify anything.",
        TabSelector(title_contains=title_contains),
        browser_session=session,
        model="gemini-3.6-flash",
        max_steps=3,
        llm_timeout=30,
        step_timeout=30,
    )
    print("=== AGENT RESULT ===")
    print(history.final_result() or history)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bounded live Browser Harness agent smoke test")
    parser.add_argument(
        "--title-contains",
        default="ChatGPT",
        help="Case-insensitive unique substring of the target tab title",
    )
    args = parser.parse_args()
    asyncio.run(main(args.title_contains))
