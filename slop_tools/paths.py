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
