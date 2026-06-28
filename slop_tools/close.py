from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import SlopError
from .git import current_branch, git_toplevel, separate_worktree
from .lifecycle import RemoveWorktreePlan, remove_worktree
from .move import run_move
from .status import validate_clean_worktree, validate_no_tracked_changes, worktree_status
from .workspaces import managed_workspace_for_repo


UNTRACKED_CLOSE_MESSAGE = "untracked files remain; run `slop mv --untracked` before closing"


@dataclass(frozen=True)
class ClosePlan:
    repo_root: Path
    control_repo: Path
    worktrees_root: Path
    repo_name: str
    branch: str


def plan_close(
    *,
    cwd: str | Path | None = None,
    worktrees_name: str = "worktrees",
) -> ClosePlan:
    start = Path.cwd() if cwd is None else Path(cwd).expanduser()
    repo_root = git_toplevel(start.resolve())
    if repo_root is None:
        raise SlopError(f"{start} is not inside a Git repository")

    workspace = managed_workspace_for_repo(repo_root, worktrees_name=worktrees_name)
    if workspace is None:
        raise SlopError(f"{repo_root} is not inside a {worktrees_name} directory")

    branch = current_branch(repo_root)
    if branch is None:
        raise SlopError("cannot close from a detached checkout")
    if branch != workspace.branch:
        raise SlopError(
            f"current branch {branch} does not match managed worktree path {workspace.branch}"
        )

    control_repo = separate_worktree(repo_root)
    if control_repo is None:
        raise SlopError("could not find a separate worktree to close from")

    return ClosePlan(
        repo_root=repo_root,
        control_repo=control_repo,
        worktrees_root=workspace.worktrees_root,
        repo_name=workspace.repo_name,
        branch=branch,
    )


def close_worktree(plan: ClosePlan, *, dry_run: bool = False) -> None:
    validate_clean_worktree(
        worktree_status(plan.repo_root),
        untracked_message=UNTRACKED_CLOSE_MESSAGE,
    )
    remove_close_worktree(plan, dry_run=dry_run)


def remove_close_worktree(
    plan: ClosePlan,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    remove_worktree(
        RemoveWorktreePlan(
            repo_root=plan.repo_root,
            control_repo=plan.control_repo,
            branch=plan.branch,
            force=force,
        ),
        dry_run=dry_run,
    )


def parse_close_args(argv: list[str], *, prog: str = "slop close") -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Close a clean managed Git worktree without deleting its branch.",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="show actions only")
    parser.add_argument(
        "--slop-untracked",
        action="store_true",
        help="move untracked files to slop before closing",
    )
    parser.add_argument(
        "--discard-untracked",
        action="store_true",
        help="discard untracked files before closing",
    )
    parser.add_argument(
        "--worktrees-name",
        default="worktrees",
        help="worktree directory name (default: worktrees)",
    )
    return parser.parse_args(argv)


def run_close(argv: list[str], *, prog: str = "slop close") -> int:
    args = parse_close_args(argv, prog=prog)
    try:
        if args.slop_untracked and args.discard_untracked:
            raise SlopError("choose only one of `--slop-untracked` or `--discard-untracked`")
        plan = plan_close(worktrees_name=args.worktrees_name)
        status = worktree_status(plan.repo_root)
        validate_no_tracked_changes(status)
        if status.untracked:
            if args.discard_untracked:
                remove_close_worktree(plan, dry_run=args.dry_run, force=True)
                return 0
            if not args.slop_untracked:
                raise SlopError(UNTRACKED_CLOSE_MESSAGE)
            move_args = ["--untracked"]
            if args.dry_run:
                move_args.append("--dry-run")
            move_result = run_move(move_args, prog=f"{prog} mv")
            if move_result != 0:
                return move_result
            if not args.dry_run:
                validate_clean_worktree(
                    worktree_status(plan.repo_root),
                    untracked_message=UNTRACKED_CLOSE_MESSAGE,
                )
        remove_close_worktree(plan, dry_run=args.dry_run)
    except SlopError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"{prog}: git command failed with exit code {exc.returncode}", file=sys.stderr)
        return 1

    return 0
