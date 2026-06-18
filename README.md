# slop-tools

`slop-tools` is a small command-line toolkit for development-only files and
matching Git worktrees in a parallel `worktrees`/`slop` directory layout.

Given a file here:

```text
/projects/acme/worktrees/example-repo/feature-branch/docs/notes.md
```

it moves the file here:

```text
/projects/acme/slop/example-repo/feature-branch/docs/notes.md
```

## Commands

### `slop mv`

Move development-only files to the matching `slop` tree.

```sh
slop mv path/to/dev-note.md another/file.md
slop mv --dry-run path/to/dev-note.md
slop mv --force path/to/dev-note.md
slop mv --untracked --dry-run
```

`--untracked` uses untracked files from the current Git worktree, as reported
by `git status`, as move inputs. You can combine it with explicit paths:

```sh
slop mv --untracked docs/extra-note.md
```

For compatibility, `mv-slop path/to/dev-note.md` also moves paths.

### `slop init`

Create a new local branch and matching worktree.

```sh
slop init ipc-updates main
slop init ipc-updates
init-slop ipc-updates main
```

`init-slop` runs `git fetch` best-effort, then creates the new branch from a
local source branch with:

```sh
git worktree add -b <new-branch> <target-path> <source-branch>
```

If the source branch is omitted, the current local branch is used. Remote refs
such as `origin/main` are intentionally rejected as source branches.

### `slop teardown`

Tear down a merged managed worktree.

```sh
slop mv --untracked
slop teardown
```

`slop teardown` refuses to run unless the current worktree has no tracked
changes, no untracked files, and its local branch is already merged into local
`main`. It runs `git fetch --prune` best-effort, but it does not pull, merge, or
update `main`.

To move untracked files to `slop` as part of teardown:

```sh
slop teardown --slop-untracked
```

Use a different local base branch with:

```sh
slop teardown --base trunk
```

## Install

Homebrew-managed Python may reject global `pip install` commands with
`externally-managed-environment`. Use `pipx` for shell-wide use instead:

```sh
pipx install --editable /path/to/slop-tools
```

From a fresh clone, that is usually:

```sh
git clone <repo-url> slop-tools
cd slop-tools
pipx install --editable .
```

If you reinstall after changing the entry points, use:

```sh
pipx install --editable --force /path/to/slop-tools
```

That installs `init-slop`, `mv-slop`, and `slop` in a dedicated virtual
environment managed by `pipx`.

If you installed an early version of this checkout when the package was named
`mv-slop`, remove that old pipx app first:

```sh
pipx uninstall mv-slop
pipx install --editable /path/to/slop-tools
```

## Detection

For existing paths inside Git repositories, the tool asks Git for the worktree
root and maps that whole root from:

```text
.../worktrees/<repository>/<branch>
```

to:

```text
.../slop/<repository>/<branch>
```

The file's path relative to the worktree root is preserved. If Git cannot find
a repository, the tool falls back to the same path shape directly.

The `worktrees`/`slop` pair can live under any container directory. For example,
`/projects/acme/worktrees/...` maps to `/projects/acme/slop/...`, while
`~/code/worktrees/...` would map to `~/code/slop/...`.

The command refuses to overwrite destinations unless `--force` is provided.

## Worktree teardown

When run from a managed worktree such as:

```text
/projects/acme/worktrees/example-repo/ipc-updates
```

`slop teardown` removes that worktree and deletes the local `ipc-updates`
branch only after verifying that `ipc-updates` is reachable from local `main`.
If local `main` is stale, update it explicitly and rerun teardown.

## Worktree creation

When run from a managed worktree such as:

```text
/projects/acme/worktrees/example-repo/main
```

`init-slop ipc-updates` creates:

```text
/projects/acme/worktrees/example-repo/ipc-updates
```

When run from a base checkout such as:

```text
/projects/acme/example-repo
```

it creates the same target path under the sibling `worktrees` directory:

```text
/projects/acme/worktrees/example-repo/ipc-updates
```
