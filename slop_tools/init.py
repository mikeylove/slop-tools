from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import SlopError
from .git import (
    current_branch,
    git_toplevel,
    local_branch_exists,
    run_git,
    validate_branch_name,
)
from .workspaces import layout_for_repo


@dataclass(frozen=True)
class InitPlan:
    repo_root: Path
    worktrees_root: Path
    repo_name: str
    new_branch: str
    source_branch: str
    target: Path


def plan_init(
    new_branch: str,
    source_branch: str | None = None,
    *,
    cwd: str | Path | None = None,
    worktrees_name: str = "worktrees",
) -> InitPlan:
    start = Path.cwd() if cwd is None else Path(cwd).expanduser()
    repo_root = git_toplevel(start.resolve())
    if repo_root is None:
        raise SlopError(f"{start} is not inside a Git repository")

    validate_branch_name(repo_root, new_branch, label="new")
    if local_branch_exists(repo_root, new_branch):
        raise SlopError(f"local branch already exists: {new_branch}")

    if source_branch is None:
        source_branch = current_branch(repo_root)
        if source_branch is None:
            raise SlopError("source branch is required from a detached checkout")

    validate_branch_name(repo_root, source_branch, label="source")
    if not local_branch_exists(repo_root, source_branch):
        raise SlopError(f"source branch must be a local branch: {source_branch}")

    layout = layout_for_repo(repo_root, worktrees_name=worktrees_name)
    target = layout.worktree_path(new_branch)
    if target.exists():
        raise SlopError(f"target worktree already exists: {target}")

    return InitPlan(
        repo_root=repo_root,
        worktrees_root=layout.worktrees_root,
        repo_name=layout.repo_name,
        new_branch=new_branch,
        source_branch=source_branch,
        target=target,
    )


def init_worktree(
    plan: InitPlan,
    *,
    dry_run: bool = False,
    fetch: bool = True,
) -> None:
    if dry_run:
        return

    if fetch:
        run_git(plan.repo_root, ["fetch", "--quiet"], check=False, quiet=True)

    plan.target.parent.mkdir(parents=True, exist_ok=True)
    run_git(
        plan.repo_root,
        [
            "worktree",
            "add",
            "-b",
            plan.new_branch,
            str(plan.target),
            plan.source_branch,
        ],
    )


def parse_init_args(argv: list[str], *, prog: str = "slop init") -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Create a Git worktree under worktrees/<repo>/<branch>.",
    )
    parser.add_argument("new_branch", help="new local branch to create")
    parser.add_argument(
        "source_branch",
        nargs="?",
        help="local branch to start from (default: current branch)",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="show action only")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="skip the best-effort git fetch before creating the worktree",
    )
    parser.add_argument(
        "--worktrees-name",
        default="worktrees",
        help="worktree directory name (default: worktrees)",
    )
    return parser.parse_args(argv)


def run_init(argv: list[str], *, prog: str = "slop init") -> int:
    args = parse_init_args(argv, prog=prog)
    try:
        plan = plan_init(
            args.new_branch,
            args.source_branch,
            worktrees_name=args.worktrees_name,
        )
        print(
            f"{plan.source_branch} -> {plan.new_branch}\n"
            f"{plan.target}"
        )
        init_worktree(plan, dry_run=args.dry_run, fetch=not args.no_fetch)
    except SlopError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"{prog}: git command failed with exit code {exc.returncode}", file=sys.stderr)
        return 1

    return 0
