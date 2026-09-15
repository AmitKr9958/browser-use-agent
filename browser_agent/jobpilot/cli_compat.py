"""Production CLI shim for the JobPilot command entry point.

The legacy ``cli.py`` parser predates the shared ``max_steps`` option on the
``prepare`` command. Keep the original module API intact while ensuring the
packaged ``jobpilot`` console command always supplies a bounded step budget.
"""

from __future__ import annotations

import argparse
import asyncio

from .cli import _run, build_parser


def _with_default_step_budget(args: argparse.Namespace) -> argparse.Namespace:
    """Add the safe default used by the packaged CLI when ``prepare`` lacks it."""
    if args.command == "prepare" and not hasattr(args, "max_steps"):
        args.max_steps = 80
    return args


def main() -> None:
    """Run the JobPilot CLI with a safe default step budget for ``prepare``."""
    args = _with_default_step_budget(build_parser().parse_args())
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
