from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import SlopError
from .git import (
    git_toplevel,
    local_branch_exists,
    remote_tracking_branch_exists,
    run_git,
    validate_branch_name,
)
from .workspaces import layout_for_repo


@dataclass(frozen=True)
class OpenPlan:
    repo_root: Path
    worktrees_root: Path
    repo_name: str
    branch: str
    source_ref: str
    create_branch: bool
    target: Path


def _local_branch_from_remote_ref(ref: str) -> str | None:
    if "/" not in ref:
        return None
    _, branch = ref.split("/", 1)
    return branch or None


def plan_open(
    branch: str,
    *,
    cwd: str | Path | None = None,
    worktrees_name: str = "worktrees",
) -> OpenPlan:
    start = Path.cwd() if cwd is None else Path(cwd).expanduser()
    repo_root = git_toplevel(start.resolve())
    if repo_root is None:
        raise SlopError(f"{start} is not inside a Git repository")

    validate_branch_name(repo_root, branch, label="open")
    source_ref = branch
    create_branch = False
    local_branch = branch
    if not local_branch_exists(repo_root, branch):
        local_branch = _local_branch_from_remote_ref(branch)
        if local_branch is None or not remote_tracking_branch_exists(repo_root, branch):
            raise SlopError(f"branch must be a local or remote-tracking branch: {branch}")
        validate_branch_name(repo_root, local_branch, label="local")
        if local_branch_exists(repo_root, local_branch):
            raise SlopError(f"local branch already exists: {local_branch}")
        source_ref = branch
        create_branch = True

    layout = layout_for_repo(repo_root, worktrees_name=worktrees_name)
    target = layout.worktree_path(local_branch)
    if target.exists():
        raise SlopError(f"target worktree already exists: {target}")

    return OpenPlan(
        repo_root=repo_root,
        worktrees_root=layout.worktrees_root,
        repo_name=layout.repo_name,
        branch=local_branch,
        source_ref=source_ref,
        create_branch=create_branch,
        target=target,
    )


def open_worktree(
    plan: OpenPlan,
    *,
    dry_run: bool = False,
    fetch: bool = True,
) -> None:
    if dry_run:
        return

    if fetch:
        run_git(plan.repo_root, ["fetch", "--quiet"], check=False, quiet=True)

    plan.target.parent.mkdir(parents=True, exist_ok=True)
    if plan.create_branch:
        run_git(
            plan.repo_root,
            [
                "worktree",
                "add",
                "--track",
                "-b",
                plan.branch,
                str(plan.target),
                plan.source_ref,
            ],
        )
    else:
        run_git(plan.repo_root, ["worktree", "add", str(plan.target), plan.branch])


def parse_open_args(argv: list[str], *, prog: str = "slop open") -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Open an existing local branch in a managed Git worktree.",
    )
    parser.add_argument("branch", help="existing local branch to open")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show action only")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="skip the best-effort git fetch before opening the worktree",
    )
    parser.add_argument(
        "--worktrees-name",
        default="worktrees",
        help="worktree directory name (default: worktrees)",
    )
    return parser.parse_args(argv)


def run_open(argv: list[str], *, prog: str = "slop open") -> int:
    args = parse_open_args(argv, prog=prog)
    try:
        if not args.dry_run and not args.no_fetch:
            start = Path.cwd()
            repo_root = git_toplevel(start.resolve())
            if repo_root is not None:
                run_git(repo_root, ["fetch", "--quiet"], check=False, quiet=True)
        plan = plan_open(args.branch, worktrees_name=args.worktrees_name)
        print(f"{plan.branch}\n{plan.target}")
        open_worktree(plan, dry_run=args.dry_run, fetch=False)
    except SlopError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"{prog}: git command failed with exit code {exc.returncode}", file=sys.stderr)
        return 1

    return 0
