from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import SlopError
from .git import run_git


TRACKED_CHANGES_MESSAGE = "tracked changes remain; commit, stash, or discard them first"
UNTRACKED_FILES_MESSAGE = (
    "untracked files remain; run `slop mv --untracked` or use `--slop-untracked`"
)


@dataclass(frozen=True)
class WorktreeStatus:
    tracked: list[str]
    untracked: list[Path]

    @property
    def clean(self) -> bool:
        return not self.tracked and not self.untracked


def worktree_status(repo: Path) -> WorktreeStatus:
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

    return WorktreeStatus(tracked=tracked, untracked=untracked)


def untracked_paths(repo: Path) -> list[Path]:
    return worktree_status(repo).untracked


def validate_no_tracked_changes(status: WorktreeStatus) -> None:
    if status.tracked:
        raise SlopError(TRACKED_CHANGES_MESSAGE)


def validate_no_untracked_files(
    status: WorktreeStatus,
    *,
    message: str = UNTRACKED_FILES_MESSAGE,
) -> None:
    if status.untracked:
        raise SlopError(message)


def validate_clean_worktree(
    status: WorktreeStatus,
    *,
    untracked_message: str = UNTRACKED_FILES_MESSAGE,
) -> None:
    validate_no_tracked_changes(status)
    validate_no_untracked_files(status, message=untracked_message)
