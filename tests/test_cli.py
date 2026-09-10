"""Pure CLI tests; no Chrome or model calls."""

from browser_agent.cli import build_parser, selector_from_args


def test_cli_list_command():
    args = build_parser().parse_args(["list"])
    assert args.command == "list"


def test_cli_selector_from_title_contains():
    args = build_parser().parse_args(["select", "--title-contains", "GitHub"])
    selector = selector_from_args(args)
    assert selector.title_contains == "GitHub"


def test_cli_selector_from_index():
    args = build_parser().parse_args(["select", "--index", "2"])
    selector = selector_from_args(args)
    assert selector.index == 2


def test_cli_run_command_parses_execution_options():
    args = build_parser().parse_args(
        [
            "run",
            "--task",
            "Read the current page title",
            "--title-contains",
            "GitHub",
            "--model",
            "gemini-3.6-flash",
            "--max-steps",
            "5",
            "--llm-timeout",
            "30",
            "--step-timeout",
            "45",
        ]
    )
    assert args.command == "run"
    assert args.task == "Read the current page title"
    assert args.model == "gemini-3.6-flash"
    assert args.max_steps == 5
    assert args.llm_timeout == 30
    assert args.step_timeout == 45
    assert selector_from_args(args).title_contains == "GitHub"
