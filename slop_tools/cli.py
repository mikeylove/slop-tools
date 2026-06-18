from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .init import run_init
from .move import run_move
from .teardown import run_teardown


def run_slop(argv: list[str], *, prog: str = "slop") -> int:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Manage development-only files and matching Git worktrees.",
    )
    parser.add_argument(
        "command",
        choices=["mv", "init", "teardown"],
        metavar="{mv,init,teardown}",
        help="command to run",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    if args.command == "mv":
        return run_move(args.args, prog=f"{prog} mv")
    if args.command == "init":
        return run_init(args.args, prog=f"{prog} init")
    if args.command == "teardown":
        return run_teardown(args.args, prog=f"{prog} teardown")

    parser.error(f"unknown command: {args.command}")


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    command_name = Path(sys.argv[0]).name if prog is None else prog

    if command_name == "init-slop":
        return run_init(args, prog="init-slop")
    if command_name == "mv-slop":
        return run_move(args, prog="mv-slop")

    return run_slop(args, prog=command_name)
