from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .errors import SlopError
from .git import git_toplevel
from .paths import ensure_child, named_ancestor
from .status import untracked_paths
from .workspaces import managed_workspace_for_repo


@dataclass(frozen=True)
class MovePlan:
    source: Path
    destination: Path
    worktrees_root: Path


def untracked_paths_from_cwd(cwd: str | Path | None = None) -> list[Path]:
    start = Path.cwd() if cwd is None else Path(cwd).expanduser()
    repo_root = git_toplevel(start.resolve())
    if repo_root is None:
        raise SlopError(f"{start} is not inside a Git repository")
    return untracked_paths(repo_root)


def _plan_from_git(
    source: Path,
    *,
    worktrees_name: str,
    slop_name: str,
) -> MovePlan | None:
    top = git_toplevel(source)
    if top is None:
        return None

    workspace = managed_workspace_for_repo(
        top,
        worktrees_name=worktrees_name,
        slop_name=slop_name,
    )
    if workspace is None:
        return None

    source_rel = ensure_child(source, top)
    if not source_rel.parts:
        raise SlopError("refusing to move an entire worktree root")

    return MovePlan(
        source,
        workspace.slop_root / workspace.key / source_rel,
        workspace.worktrees_root,
    )


def _plan_from_path_shape(
    source: Path,
    *,
    worktrees_name: str,
    slop_name: str,
) -> MovePlan:
    worktrees_root = named_ancestor(source, worktrees_name)
    if worktrees_root is None:
        raise SlopError(f"{source} is not inside a {worktrees_name} directory")

    rel = ensure_child(source, worktrees_root)
    if len(rel.parts) < 3:
        raise SlopError(
            f"{source} does not look like {worktrees_name}/<repository>/<branch>/<path>"
        )

    slop_root = worktrees_root.parent / slop_name
    return MovePlan(source, slop_root / rel, worktrees_root)


def plan_move(
    path: str | Path,
    *,
    worktrees_name: str = "worktrees",
    slop_name: str = "slop",
) -> MovePlan:
    source = Path(path).expanduser()
    if not source.exists():
        raise SlopError(f"{source} does not exist")

    source = source.resolve()
    return _plan_from_git(
        source,
        worktrees_name=worktrees_name,
        slop_name=slop_name,
    ) or _plan_from_path_shape(
        source,
        worktrees_name=worktrees_name,
        slop_name=slop_name,
    )


def move(plan: MovePlan, *, dry_run: bool = False, force: bool = False) -> None:
    destination = plan.destination
    if destination.exists():
        if not force:
            raise SlopError(f"{destination} already exists; use --force to replace it")
        if dry_run:
            return
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    if dry_run:
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(plan.source), str(destination))
    _prune_empty_parents(plan.source.parent, stop_at=plan.worktrees_root)


def _prune_empty_parents(path: Path, *, stop_at: Path | None) -> None:
    if stop_at is None:
        return

    current = path
    while current != stop_at and current != current.parent:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent


def parse_move_args(argv: list[str], *, prog: str = "slop mv") -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="Move files from worktrees/<repo>/<branch> to slop/<repo>/<branch>.",
    )
    parser.add_argument("paths", nargs="*", help="files or directories to move")
    parser.add_argument(
        "-u",
        "--untracked",
        action="store_true",
        help="move untracked files from the current Git worktree",
    )
    parser.add_argument("-n", "--dry-run", action="store_true", help="show moves only")
    parser.add_argument("-f", "--force", action="store_true", help="replace destinations")
    parser.add_argument(
        "--worktrees-name",
        default="worktrees",
        help="source tree directory name (default: worktrees)",
    )
    parser.add_argument(
        "--slop-name",
        default="slop",
        help="destination tree directory name (default: slop)",
    )
    return parser.parse_args(argv)


def run_move(argv: list[str], *, prog: str = "slop mv") -> int:
    args = parse_move_args(argv, prog=prog)
    try:
        paths = list(args.paths)
        if args.untracked:
            paths.extend(untracked_paths_from_cwd())
        if not paths:
            raise SlopError("provide paths or use --untracked")

        plans = [
            plan_move(
                path,
                worktrees_name=args.worktrees_name,
                slop_name=args.slop_name,
            )
            for path in paths
        ]

        for plan in plans:
            print(f"{plan.source} -> {plan.destination}")
            move(plan, dry_run=args.dry_run, force=args.force)
    except SlopError as exc:
        print(f"{prog}: {exc}", file=sys.stderr)
        return 1

    return 0
