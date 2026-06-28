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

### `slop init`

Create a new local branch and matching worktree.

```sh
slop init ipc-updates main
slop init ipc-updates
```

`slop init` runs `git fetch` best-effort, then creates the new branch from a
local source branch with:

```sh
git worktree add -b <new-branch> <target-path> <source-branch>
```

If the source branch is omitted, the current local branch is used. Remote refs
such as `origin/main` are intentionally rejected as source branches.

### `slop open`

Open an existing local or remote-tracking branch in a matching worktree.

```sh
slop open feature-branch
slop open origin/feature-branch
```

`slop open` runs `git fetch` best-effort. For an existing local branch, it
checks out the branch with:

```sh
git worktree add <target-path> <branch>
```

For a remote-tracking branch, it creates a local tracking branch and checks it
out with:

```sh
git worktree add --track -b <local-branch> <target-path> <remote>/<branch>
```

The target path uses the same `worktrees/<repo>/<branch>` layout as
`slop init`. Branch slashes are preserved as nested directories; for example,
`feature/actual-description` maps to
`worktrees/<repo>/feature/actual-description`. The command refuses target paths
that already exist or conflict with a managed worktree parent.

### `slop close`

Close a clean managed worktree without deleting its branch.

```sh
slop close
```

`slop close` refuses tracked changes and untracked files. Unlike
`slop teardown`, it does not require the branch to be merged into a base branch,
and it does not delete the local branch.

To move untracked files to `slop` as part of close:

```sh
slop close --slop-untracked
```

To discard untracked files as part of close:

```sh
slop close --discard-untracked
```

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

That installs `slop` in a dedicated virtual environment managed by `pipx`.

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

`slop init ipc-updates` creates:

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

## Worktree opening

When run from a base checkout such as:

```text
/projects/acme/example-repo
```

`slop open feature-branch` opens the existing local branch at:

```text
/projects/acme/worktrees/example-repo/feature-branch
```

`slop open origin/feature-branch` creates a local `feature-branch` branch that
tracks `origin/feature-branch` and opens it at the same path.

## Worktree closing

When run from a clean managed worktree such as:

```text
/projects/acme/worktrees/example-repo/feature-branch
```

`slop close` removes that worktree and leaves the local `feature-branch` branch
intact.

Use `slop close --slop-untracked` to preserve untracked files in the matching
`slop` tree before removing the worktree.

Use `slop close --discard-untracked` to delete untracked files before removing
the worktree.
