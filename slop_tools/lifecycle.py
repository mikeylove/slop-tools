from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .git import run_git
from .paths import prune_empty_dirs


def slop_dir_note(slop_dir: Path) -> str:
    if slop_dir.is_dir() and any(slop_dir.iterdir()):
        return " (existing files)"
    return ""


def prune_empty_slop_dir(slop_dir: Path, *, slop_root: Path, dry_run: bool = False) -> None:
    if not slop_dir.is_dir() or any(slop_dir.iterdir()):
        return

    print(f"remove empty slop dir {slop_dir}")
    if dry_run:
        return
    prune_empty_dirs(slop_dir, stop_at=slop_root)


@dataclass(frozen=True)
class RemoveWorktreePlan:
    repo_root: Path
    control_repo: Path
    branch: str
    delete_branch: bool = False
    force: bool = False


def remove_worktree(plan: RemoveWorktreePlan, *, dry_run: bool = False) -> None:
    print(f"remove worktree {plan.repo_root}")
    if plan.delete_branch:
        print(f"delete branch {plan.branch}")
    if dry_run:
        return

    os.chdir(plan.control_repo)
    remove_args = ["worktree", "remove"]
    if plan.force:
        remove_args.append("--force")
    remove_args.append(str(plan.repo_root))
    run_git(plan.control_repo, remove_args)
    if plan.delete_branch:
        run_git(plan.control_repo, ["branch", "-d", plan.branch])
