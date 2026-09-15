"""Regression coverage for the packaged JobPilot CLI shim."""

from argparse import Namespace

from browser_agent.jobpilot.cli_compat import _with_default_step_budget


def test_prepare_command_gets_default_step_budget() -> None:
    args = _with_default_step_budget(Namespace(command="prepare"))
    assert args.max_steps == 80


def test_other_commands_are_not_modified() -> None:
    args = Namespace(command="apply", max_steps=25)
    assert _with_default_step_budget(args) is args
    assert args.max_steps == 25
