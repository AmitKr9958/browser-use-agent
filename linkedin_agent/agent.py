"""LinkedIn workflow runner built on Browser Use and a real Chrome profile."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from browser_use import Agent, Browser, ChatOpenAI


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def choose_profile(config: dict[str, Any]) -> str | None:
    configured = config.get("chrome", {}).get("profile_directory")
    if configured:
        return configured

    profiles = Browser.list_chrome_profiles()
    if not profiles:
        return None

    print("Available Chrome profiles:")
    for index, profile in enumerate(profiles, 1):
        print(f"  {index}. {profile['name']}")

    while True:
        choice = input(f"Select profile (1-{len(profiles)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(profiles):
            return profiles[int(choice) - 1]["directory"]
        print("Invalid choice.")


def build_task(config: dict[str, Any], task_name: str) -> str:
    linkedin = config.get("linkedin", {})
    caps = linkedin.get("daily_caps", {})
    jobs = linkedin.get("job_search", {})
    locations = ", ".join(jobs.get("locations", []))
    titles = ", ".join(jobs.get("titles", []))
    posted = jobs.get("posted_within_hours", 72)
    exclusions = ", ".join(jobs.get("exclude", []))

    common = (
        "Operate only on LinkedIn. Use the existing logged-in browser session. "
        "Do not bypass CAPTCHA, MFA, security checks, rate limits, or account restrictions. "
        "Do not fabricate profile, company, job, or conversation information. "
        f"Configured mode is {linkedin.get('mode', 'review')}. "
        f"Daily caps are {json.dumps(caps)}. "
    )

    tasks = {
        "login-check": (
            common
            + "Open LinkedIn and verify whether the account is already logged in. "
            "Return the visible account identity if available. Do not change account settings."
        ),
        "job-search": (
            common
            + f"Search LinkedIn Jobs for these target titles: {titles}. "
            f"Preferred locations: {locations}. Only consider jobs posted within the last {posted} hours. "
            f"Exclude roles matching: {exclusions}. "
            "Return a structured shortlist with title, company, location, posting age, application route and URL. "
            "Do not apply to any job."
        ),
        "recruiter-research": (
            common
            + "Using the user's configured job-search criteria, identify relevant recruiters or hiring managers "
            "for shortlisted roles where LinkedIn exposes that information. Build a research list and draft, but do not send messages."
        ),
        "content-draft": (
            common
            + "Review the current LinkedIn feed for themes relevant to Power BI, Microsoft Fabric, BI, analytics and AI. "
            "Draft up to two original LinkedIn posts in the user's professional voice. Do not publish."
        ),
        "daily-run": (
            common
            + "Perform the daily LinkedIn workflow: check login, research matching jobs, research relevant recruiters, "
            "review useful feed themes, and prepare drafts for outreach/content. "
            "Do not send connection requests, direct messages, comments or posts unless the configured approval gate is satisfied."
        ),
    }

    if task_name not in tasks:
        raise ValueError(f"Unknown task: {task_name}")
    return tasks[task_name]


async def run(config_path: Path, task_name: str) -> None:
    config = load_config(config_path)
    profile = choose_profile(config)
    browser = Browser.from_system_chrome(profile_directory=profile)

    task = build_task(config, task_name)
    agent = Agent(
        task=task,
        llm=ChatOpenAI(model="gpt-5.6-luna"),
        browser=browser,
    )
    history = await agent.run()

    log_path = Path(config.get("activity_log", {}).get("path", "linkedin_agent/data/activity.jsonl"))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "task": task_name,
        "result": history.final_result(),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    print(history.final_result())


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn Browser Use agent")
    parser.add_argument("--config", type=Path, default=Path("linkedin_agent/config.yaml"))
    parser.add_argument(
        "--task",
        choices=["login-check", "job-search", "recruiter-research", "content-draft", "daily-run"],
        default="login-check",
    )
    args = parser.parse_args()
    asyncio.run(run(args.config, args.task))


if __name__ == "__main__":
    main()
