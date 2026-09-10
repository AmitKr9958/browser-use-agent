"""CLI execution tests using mocked agent orchestration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import browser_agent.cli as cli


@pytest.mark.asyncio
async def test_main_async_run_prints_json(monkeypatch, capsys):
    history = SimpleNamespace(final_result=lambda: "hello")

    async def fake_run_on_tab(task, selector, **kwargs):
        assert task == "Read title"
        assert selector.title_contains == "9Router"
        assert kwargs == {
            "model": "gemini-3.6-flash",
            "max_steps": 5,
            "llm_timeout": 30,
            "step_timeout": 40,
        }
        return history

    monkeypatch.setattr(cli, "run_on_tab", fake_run_on_tab)
    args = cli.build_parser().parse_args(
        [
            "run",
            "--task",
            "Read title",
            "--title-contains",
            "9Router",
            "--max-steps",
            "5",
            "--llm-timeout",
            "30",
            "--step-timeout",
            "40",
        ]
    )

    assert await cli.main_async(args) == 0
    assert capsys.readouterr().out == '{\n  "success": true,\n  "result": "hello"\n}\n'
