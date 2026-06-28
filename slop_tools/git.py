from __future__ import annotations

import subprocess
from pathlib import Path

from .errors import SlopError


def run_git(
    repo: Path,
    args: list[str],
    *,
    check: bool = True,
    capture: bool = False,
    quiet: bool = False,
) -> subprocess.CompletedProcess[str]:
    stdout = subprocess.PIPE if capture else None
    stderr = subprocess.PIPE if capture else (subprocess.DEVNULL if quiet else None)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        stdout=stdout,
        stderr=stderr,
        text=True,
    )


def git_toplevel(path: Path) -> Path | None:
    start = path if path.is_dir() else path.parent
    try:
        result = run_git(start, ["rev-parse", "--show-toplevel"], capture=True, quiet=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    value = result.stdout.strip()
    return Path(value).resolve() if value else None


def validate_branch_name(repo: Path, branch: str, *, label: str) -> None:
    try:
        run_git(repo, ["check-ref-format", "--branch", branch], capture=True, quiet=True)
    except subprocess.CalledProcessError as exc:
        raise SlopError(f"{label} branch name is not valid: {branch}") from exc


def local_branch_exists(repo: Path, branch: str) -> bool:
    result = run_git(
        repo,
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        check=False,
        quiet=True,
    )
    return result.returncode == 0


def remote_tracking_branch_exists(repo: Path, branch: str) -> bool:
    result = run_git(
        repo,
        ["show-ref", "--verify", "--quiet", f"refs/remotes/{branch}"],
        check=False,
        quiet=True,
    )
    return result.returncode == 0


def current_branch(repo: Path) -> str | None:
    result = run_git(
        repo,
        ["symbolic-ref", "--quiet", "--short", "HEAD"],
        check=False,
        capture=True,
        quiet=True,
    )
    branch = result.stdout.strip() if result.returncode == 0 else ""
    return branch or None


def worktree_for_branch(repo: Path, branch: str) -> Path | None:
    branch_ref = f"refs/heads/{branch}"
    for worktree, record_branch in _worktree_records(repo):
        if record_branch == branch_ref:
            return worktree
    return None


def separate_worktree(repo: Path) -> Path | None:
    repo = repo.resolve()
    for worktree, _ in _worktree_records(repo):
        if worktree != repo:
            return worktree
    return None


def _worktree_records(repo: Path) -> list[tuple[Path, str | None]]:
    result = run_git(repo, ["worktree", "list", "--porcelain"], capture=True)
    records = result.stdout.strip().split("\n\n")
    parsed: list[tuple[Path, str | None]] = []
    for record in records:
        worktree: Path | None = None
        record_branch: str | None = None
        for line in record.splitlines():
            if line.startswith("worktree "):
                worktree = Path(line.removeprefix("worktree ")).resolve()
            elif line.startswith("branch "):
                record_branch = line.removeprefix("branch ")
        if worktree is not None:
            parsed.append((worktree, record_branch))
    return parsed
