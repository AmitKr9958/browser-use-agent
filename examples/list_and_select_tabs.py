"""List real Chrome tabs and select one deterministically.

Run after Browser Harness has connected to Chrome:
    uv run python examples/list_and_select_tabs.py
"""

import asyncio

from browser_agent.connection import connect_browser_harness
from browser_agent.tabs import TabManager, TabSelector


async def main() -> None:
    manager = TabManager(connect_browser_harness())
    tabs = await manager.list_tabs()
    print(f"Open tabs: {len(tabs)}")
    for tab in tabs:
        print(f"[{tab.index}] {tab.title}\n    {tab.url}\n    target={tab.target_id}")

    if tabs:
        selected = await manager.select_tab(TabSelector(target_id=tabs[0].target_id))
        print(f"\nVerified selection: [{selected.index}] {selected.title}")


if __name__ == "__main__":
    asyncio.run(main())
