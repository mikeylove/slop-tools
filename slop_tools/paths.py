from __future__ import annotations

from pathlib import Path

from .errors import SlopError


def named_ancestor(path: Path, name: str) -> Path | None:
    for parent in (path, *path.parents):
        if parent.name == name:
            return parent
    return None


def ensure_child(path: Path, parent: Path) -> Path:
    try:
        return path.relative_to(parent)
    except ValueError as exc:
        raise SlopError(f"{path} is not inside {parent}") from exc


def prune_empty_dirs(path: Path, *, stop_at: Path | None) -> None:
    if stop_at is None:
        return

    current = path
    while current != stop_at and current != current.parent:
        try:
            current.rmdir()
        except OSError:
            return
        current = current.parent
