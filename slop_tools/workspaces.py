from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import SlopError
from .paths import ensure_child, named_ancestor


@dataclass(frozen=True)
class WorkspaceLayout:
    worktrees_root: Path
    slop_root: Path
    repo_name: str

    def worktree_path(self, branch: str) -> Path:
        return self.worktrees_root / self.repo_name / branch_path(branch)


@dataclass(frozen=True)
class ManagedWorkspace:
    repo_root: Path
    layout: WorkspaceLayout
    branch: str

    @property
    def worktrees_root(self) -> Path:
        return self.layout.worktrees_root

    @property
    def slop_root(self) -> Path:
        return self.layout.slop_root

    @property
    def repo_name(self) -> str:
        return self.layout.repo_name

    @property
    def key(self) -> Path:
        return Path(self.repo_name) / branch_path(self.branch)


def branch_path(branch: str) -> Path:
    return Path(*branch.split("/"))


def layout_for_repo(
    repo_root: Path,
    *,
    worktrees_name: str = "worktrees",
    slop_name: str = "slop",
) -> WorkspaceLayout:
    worktrees_root = named_ancestor(repo_root, worktrees_name)
    if worktrees_root is None:
        worktrees_root = repo_root.parent / worktrees_name
        repo_name = repo_root.name
    else:
        rel = ensure_child(repo_root, worktrees_root)
        if len(rel.parts) < 2:
            raise SlopError(
                f"{repo_root} does not look like {worktrees_name}/<repository>/<branch>"
            )
        repo_name = rel.parts[0]

    return WorkspaceLayout(
        worktrees_root=worktrees_root,
        slop_root=worktrees_root.parent / slop_name,
        repo_name=repo_name,
    )


def managed_workspace_for_repo(
    repo_root: Path,
    *,
    worktrees_name: str = "worktrees",
    slop_name: str = "slop",
) -> ManagedWorkspace | None:
    worktrees_root = named_ancestor(repo_root, worktrees_name)
    if worktrees_root is None:
        return None

    rel = ensure_child(repo_root, worktrees_root)
    if len(rel.parts) < 2:
        raise SlopError(
            f"{repo_root} does not look like {worktrees_name}/<repository>/<branch>"
        )

    repo_name = rel.parts[0]
    branch = "/".join(rel.parts[1:])
    layout = WorkspaceLayout(
        worktrees_root=worktrees_root,
        slop_root=worktrees_root.parent / slop_name,
        repo_name=repo_name,
    )
    return ManagedWorkspace(repo_root=repo_root, layout=layout, branch=branch)
