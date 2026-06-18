from __future__ import annotations

import argparse
import os
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
    worktree_for_branch,
)
from .move import run_move
from .paths import ensure_child, named_ancestor


PROTECTED_BRANCHES = {"main", "master", "trunk", "develop"}


@dataclass(frozen=True)
class TeardownPlan:
    repo_root: Path
    control_repo: Path
    worktrees_root: Path
    repo_name: str
    branch: str
    base_branch: str


def _branch_from_managed_path(
    repo_root: Path,
    worktrees_root: Path,
    *,
    worktrees_name: str,
) -> tuple[str, str]:
    rel = ensure_child(repo_root, worktrees_root)
    if len(rel.parts) < 2:
        raise SlopError(f"{repo_root} does not look like {worktrees_name}/<repository>/<branch>")
    return rel.parts[0], "/".join(rel.parts[1:])


def _worktree_status(repo: Path) -> tuple[list[str], list[Path]]:
    result = run_git(
        repo,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
        capture=True,
    )
    tracked: list[str] = []
    untracked: list[Path] = []
    entries = result.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue

        status = entry[:2]
        path = entry[3:]
        if status == "??":
            untracked.append(repo / path)
        else:
            tracked.append(path)

        if "R" in status or "C" in status:
            index += 1

    return tracked, untracked


def plan_teardown(
    *,
    cwd: str | Path | None = None,
    base_branch: str = "main",
    worktrees_name: str = "worktrees",
) -> TeardownPlan:
    start = Path.cwd() if cwd is None else Path(cwd).expanduser()
    repo_root = git_toplevel(start.resolve())
    if repo_root is None:
        raise SlopError(f"{start} is not inside a Git repository")

    worktrees_root = named_ancestor(repo_root, worktrees_name)
    if worktrees_root is None:
        raise SlopError(f"{repo_root} is not inside a {worktrees_name} directory")

    repo_name, managed_branch = _branch_from_managed_path(
        repo_root,
        worktrees_root,
        worktrees_name=worktrees_name,
    )
    branch = current_branch(repo_root)
    if branch is None:
        raise SlopError("cannot teardown from a detached checkout")
    if branch != managed_branch:
        raise SlopError(
            f"current branch {branch} does not match managed worktree path {managed_branch}"
        )
    if branch in PROTECTED_BRANCHES:
        raise SlopError(f"refusing to teardown protected branch: {branch}")
    if branch == base_branch:
        raise SlopError("branch and base branch are the same")
    if not local_branch_exists(repo_root, base_branch):
        raise SlopError(f"base branch must be a local branch: {base_branch}")

    control_repo = worktree_for_branch(repo_root, base_branch)
    if control_repo is None or control_repo == repo_root:
        raise SlopError(f"could not find a separate worktree for base branch: {base_branch}")

    return TeardownPlan(
        repo_root=repo_root,
        control_repo=control_repo,
        worktrees_root=worktrees_root,
        repo_name=repo_name,
        branch=branch,
        base_branch=base_branch,
    )


def validate_teardown_clean(plan: TeardownPlan) -> None:
    tracked, untracked = _worktree_status(plan.repo_root)
    if tracked:
        raise SlopError("tracked changes remain; commit, stash, or discard them first")
    if untracked:
        raise SlopError("untracked files remain; run `slop mv --untracked` or use `--slop-untracked`")


def validate_teardown_merged(plan: TeardownPlan) -> None:
    result = run_git(
        plan.repo_root,
        ["merge-base", "--is-ancestor", plan.branch, plan.base_branch],
        check=False,
        quiet=True,
    )
    if result.returncode != 0:
        raise SlopError(f"{plan.branch} is not merged into local {plan.base_branch}")


def teardown(plan: TeardownPlan, *, dry_run: bool = False, fetch: bool = True) -> None:
    if fetch:
        run_git(plan.control_repo, ["fetch", "--prune", "--quiet"], check=False, quiet=True)

    validate_teardown_merged(plan)

    print(f"{plan.branch} merged into {plan.base_branch}")
    print(f"remove worktree {plan.repo_root}")
    print(f"delete branch {plan.branch}")
    if dry_run:
        return

    os.chdir(plan.control_repo)
    run_git(plan.control_repo, ["worktree", "remove", str(plan.repo_root)])
    run_git(plan.control_repo, ["branch", "-d", plan.branch])


def parse_teardown_args(argv: list[str], *, prog: str = "slop teardown") -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Remove a merged managed worktree and delete its local branch.",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="show actions only")
    parser.add_argument(
        "--base",
        default="main",
        help="local branch that must contain this branch (default: main)",
    )
    parser.add_argument(
        "--slop-untracked",
        action="store_true",
        help="move untracked files to slop before tearing down",
    )
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="skip the best-effort git fetch --prune before checking merge status",
    )
    parser.add_argument(
        "--worktrees-name",
        default="worktrees",
        help="worktree directory name (default: worktrees)",
    )
    return parser.parse_args(argv)


def run_teardown(argv: list[str], *, prog: str = "slop teardown") -> int:
    args = parse_teardown_args(argv, prog=prog)
    try:
        plan = plan_teardown(base_branch=args.base, worktrees_name=args.worktrees_name)
        tracked, untracked = _worktree_status(plan.repo_root)
        if tracked:
            raise SlopError("tracked changes remain; commit, stash, or discard them first")
        if untracked:
            if not args.slop_untracked:
                raise SlopError(
                    "untracked files remain; run `slop mv --untracked` or use `--slop-untracked`"
                )
            move_args = ["--untracked"]
            if args.dry_run:
                move_args.append("--dry-run")
            move_result = run_move(move_args, prog=f"{prog} mv")
            if move_result != 0:
                return move_result
            if not args.dry_run:
                validate_teardown_clean(plan)
        else:
            validate_teardown_clean(plan)

        teardown(plan, dry_run=args.dry_run, fetch=not args.no_fetch)
    except SlopError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"{prog}: git command failed with exit code {exc.returncode}", file=sys.stderr)
        return 1

    return 0
