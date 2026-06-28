from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .git import run_git


@dataclass(frozen=True)
class RemoveWorktreePlan:
    repo_root: Path
    control_repo: Path
    branch: str
    delete_branch: bool = False


def remove_worktree(plan: RemoveWorktreePlan, *, dry_run: bool = False) -> None:
    print(f"remove worktree {plan.repo_root}")
    if plan.delete_branch:
        print(f"delete branch {plan.branch}")
    if dry_run:
        return

    os.chdir(plan.control_repo)
    run_git(plan.control_repo, ["worktree", "remove", str(plan.repo_root)])
    if plan.delete_branch:
        run_git(plan.control_repo, ["branch", "-d", plan.branch])
