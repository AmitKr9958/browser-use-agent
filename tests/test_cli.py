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
