from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass

from .close import run_close
from .init import run_init
from .move import run_move
from .open import run_open
from .teardown import run_teardown


@dataclass(frozen=True)
class Command:
    name: str
    run: Callable[..., int]


COMMANDS = (
    Command("mv", run_move),
    Command("init", run_init),
    Command("open", run_open),
    Command("close", run_close),
    Command("teardown", run_teardown),
)
COMMAND_BY_NAME = {command.name: command for command in COMMANDS}


def run_slop(argv: list[str], *, prog: str = "slop") -> int:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Manage development-only files and matching Git worktrees.",
    )
    parser.add_argument(
        "command",
        choices=list(COMMAND_BY_NAME),
        metavar="{" + ",".join(COMMAND_BY_NAME) + "}",
        help="command to run",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    command = COMMAND_BY_NAME[args.command]
    return command.run(args.args, prog=f"{prog} {command.name}")


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    return run_slop(args, prog="slop" if prog is None else prog)
