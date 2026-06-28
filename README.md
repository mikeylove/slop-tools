# slop-tools

`slop-tools` manages development-only files and matching Git worktrees in a
parallel `worktrees`/`slop` directory layout.

It is built around two worktree lifecycles:

- Owned work: `slop init` -> `slop teardown`
- Review or disposable work: `slop open` -> `slop close`

## Layout

Managed worktrees live under:

```text
.../worktrees/<repository>/<branch>
```

Development-only files can be preserved under the matching `slop` tree:

```text
.../slop/<repository>/<branch>
```

For example, this file:

```text
/projects/acme/worktrees/example-repo/feature-branch/docs/notes.md
```

maps to:

```text
/projects/acme/slop/example-repo/feature-branch/docs/notes.md
```

Branch slashes are preserved as nested directories. For example,
`feature/actual-description` maps to:

```text
.../worktrees/<repository>/feature/actual-description
```

The `worktrees`/`slop` pair can live under any container directory.

## Workflows

### Start Owned Work

Create a new local branch and matching worktree:

```sh
slop init ipc-updates main
slop init ipc-updates
```

If the source branch is omitted, the current local branch is used. Remote refs
such as `origin/main` are intentionally rejected as source branches.

When run from:

```text
/projects/acme/example-repo
```

`slop init ipc-updates` creates:

```text
/projects/acme/worktrees/example-repo/ipc-updates
```

### Finish Owned Work

Tear down an owned worktree only after it has landed:

```sh
slop teardown
```

`slop teardown` refuses to run unless the current worktree has no tracked
changes, no untracked files, and its local branch is already merged into local
`main`. It removes the worktree and deletes the local branch.

To move untracked files to `slop` as part of teardown:

```sh
slop teardown --slop-untracked
```

Use a different local base branch with:

```sh
slop teardown --base trunk
```

### Open Existing Work

Open an existing local or remote-tracking branch in a managed worktree:

```sh
slop open feature-branch
slop open origin/feature-branch
```

For a remote-tracking branch, `slop open` creates a local tracking branch.
`slop open origin/feature-branch` opens:

```text
/projects/acme/worktrees/example-repo/feature-branch
```

### Close Existing Work

Close a review or disposable worktree without requiring a merge check and
without deleting the local branch:

```sh
slop close
```

`slop close` refuses tracked changes and requires an explicit choice for
untracked files:

```sh
slop close --slop-untracked
slop close --discard-untracked
```

`--slop-untracked` preserves untracked files in the matching `slop` tree.
`--discard-untracked` deletes untracked files before removing the worktree.

### Preserve Artifacts

Move development-only files to the matching `slop` tree:

```sh
slop mv path/to/dev-note.md another/file.md
slop mv --untracked
slop mv --dry-run path/to/dev-note.md
slop mv --force path/to/dev-note.md
```

`--untracked` uses untracked files from the current Git worktree, as reported
by `git status`, as move inputs. You can combine it with explicit paths:

```sh
slop mv --untracked docs/extra-note.md
```

## Command Reference

### `slop init`

Create a new local branch and matching worktree.

```sh
slop init [-n] [--no-fetch] [--worktrees-name NAME] <new-branch> [source-branch]
```

`slop init` runs `git fetch` best-effort, then creates the new branch with:

```sh
git worktree add -b <new-branch> <target-path> <source-branch>
```

### `slop open`

Open an existing local or remote-tracking branch in a matching worktree.

```sh
slop open [-n] [--no-fetch] [--worktrees-name NAME] <branch-or-remote>
```

For a local branch, it runs:

```sh
git worktree add <target-path> <branch>
```

For a remote-tracking branch, it runs:

```sh
git worktree add --track -b <local-branch> <target-path> <remote>/<branch>
```

The command refuses target paths that already exist or conflict with a managed
worktree parent.

### `slop close`

Close a managed worktree without deleting its branch.

```sh
slop close [-n] [--slop-untracked | --discard-untracked] [--worktrees-name NAME]
```

Tracked changes always block close. Untracked files block close unless one of
the explicit untracked flags is provided.

### `slop teardown`

Remove a merged managed worktree and delete its local branch.

```sh
slop teardown [-n] [--base BRANCH] [--slop-untracked] [--no-fetch] [--worktrees-name NAME]
```

`slop teardown` runs `git fetch --prune` best-effort, but it does not pull,
merge, or update the base branch. If local `main` or another base is stale,
update it explicitly and rerun teardown.

### `slop mv`

Move files from `worktrees/<repo>/<branch>` to `slop/<repo>/<branch>`.

```sh
slop mv [-u] [-n] [-f] [--worktrees-name NAME] [--slop-name NAME] [paths ...]
```

The command refuses to overwrite destinations unless `--force` is provided.

## Install

Homebrew-managed Python may reject global `pip install` commands with
`externally-managed-environment`. Use `pipx` for shell-wide use instead:

```sh
pipx install --editable /path/to/slop-tools
```

From a fresh clone:

```sh
git clone <repo-url> slop-tools
cd slop-tools
pipx install --editable .
```

If you reinstall after changing entry points:

```sh
pipx install --editable --force /path/to/slop-tools
```

That installs `slop` in a dedicated virtual environment managed by `pipx`.

## Details

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
a repository, `slop mv` falls back to the same path shape directly.

The current roadmap lives in [ROADMAP.md](ROADMAP.md).
