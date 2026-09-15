"""Production CLI shim for the JobPilot command entry point.

The legacy ``cli.py`` parser predates the shared ``max_steps`` option on the
``prepare`` command.  Keep the original module API intact while ensuring the
packaged ``jobpilot`` console command always supplies a bounded step budget.
"""

from __future__ import annotations

import asyncio

from .cli import _run, build_parser


def main() -> None:
    """Run the JobPilot CLI with a safe default step budget for ``prepare``."""
    args = build_parser().parse_args()
    if args.command == "prepare" and not hasattr(args, "max_steps"):
        args.max_steps = 80
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
