---
name: slop
description: Manage Git worktrees and development-only files with the user's `slop` CLI. Use this whenever the user wants to start work on a new branch, set up or spin up a worktree, check out an existing or PR branch for review, close/remove/tear down a worktree, clean up a finished branch, or move scratch files (notes, probe scripts, debug files, dev-only junk) out of a repo before committing. Trigger even when the user doesn't say "slop" — any task involving creating, opening, or removing git worktrees, or preserving uncommittable dev files, should go through `slop` instead of raw `git worktree` or ad-hoc `mv` commands.
---

# slop — managed worktrees and dev-only file trees

`slop` is the user's CLI for Git worktrees. It keeps every worktree in a
predictable place and pairs it with a parallel "slop" tree where
development-only files (notes, repro scripts, scratch output) are preserved
without ever entering the repo:

```text
<container>/<repo>                      # primary checkout
<container>/worktrees/<repo>/<branch>   # managed worktrees
<container>/slop/<repo>/<branch>        # preserved dev-only files
```

Branch names containing `/` become nested directories
(`worktrees/<repo>/feature/thing`). Commands infer the repo, branch, and
container from the current directory, so always `cd` into the repo or worktree
you want to act on before running `slop`.

`init` and `open` create the branch's slop dir alongside the worktree and
print its path — dev-only notes and scratch files can be written straight
into it from the start, no manual path mapping or `mkdir` needed. `close` and
`teardown` prune the slop dir again if it is still empty, so a surviving slop
dir always means something was preserved there.

Prefer `slop` over raw `git worktree` commands whenever this layout applies:
hand-rolled worktrees end up in unpredictable places and lose the matching
slop tree.

## Choosing the right command

| Situation | Command |
|---|---|
| Start new owned work on a new branch | `slop init <new-branch> [source-branch]` |
| Check out an existing or PR branch for review | `slop open <branch>` or `slop open origin/<branch>` |
| Done with a review/disposable worktree, keep the branch | `slop close` |
| Owned work has merged; remove worktree and branch | `slop teardown` |
| Move dev-only files out of a worktree | `slop mv <paths…>` or `slop mv --untracked` |

**init vs open**: `init` creates a *new* local branch (source defaults to the
current branch; remote refs like `origin/main` are rejected as sources — use
the local branch). `open` uses an *existing* branch; given a remote-tracking
ref it creates a local tracking branch first.

**close vs teardown**: `close` removes only the worktree and keeps the local
branch — right for reviews and disposable checkouts. `teardown` also deletes
the local branch, and refuses unless the worktree is completely clean and the
branch is already merged into local `main` (override with `--base <branch>`).

## Untracked files at close/teardown

Tracked changes always block `close` and `teardown`; commit or stash them
first — the tool never offers to discard them. Untracked files require an
explicit decision:

- `slop close --slop-untracked` — preserve them in the matching slop tree.
  Default to this when the user hasn't said the files are disposable.
- `slop close --discard-untracked` — delete them. Only when the user clearly
  wants them gone.
- `slop teardown --slop-untracked` — same preservation during teardown.

## slop mv

`slop mv` moves files from a *managed worktree* into the matching slop tree,
preserving each file's path relative to the worktree root:

```text
worktrees/<repo>/<branch>/scripts/probe.lua  ->  slop/<repo>/<branch>/scripts/probe.lua
```

- `slop mv --untracked` moves everything `git status` reports as untracked in
  the current worktree; it can be combined with explicit paths.
- It only works on paths under a `worktrees/` directory. From a primary
  checkout it fails with "not inside a worktrees directory" — that is by
  design, not a bug to work around.
- It refuses to overwrite existing destinations unless `--force`, and refuses
  to move an entire worktree root.

## Working habits

- Run `close` and `teardown` from inside the worktree being removed. Afterward
  `cd` back to the primary checkout — the directory you were standing in no
  longer exists, so any further command in the old cwd will fail.
- Every subcommand accepts `-n`/`--dry-run`. Use it first for `teardown` and
  whenever the path mapping isn't obvious, then run for real.
- `init`, `open`, and `teardown` run a best-effort `git fetch` first; pass
  `--no-fetch` when offline or when the fetch is known to be pointless.
- `teardown` never updates the base branch. If it refuses because local `main`
  is stale, update it (e.g. `git -C <primary-checkout> pull --ff-only`) and
  rerun teardown.
- `slop` is deliberately conservative: a refusal means a safety condition is
  unmet. Report the refusal and resolve the underlying condition — do not
  bypass it with raw `git worktree remove --force` or `git branch -D`.

## Examples

Start a feature off `main` and enter its worktree:

```sh
cd /projects/acme/example-repo
slop init ipc-updates main
cd ../worktrees/example-repo/ipc-updates
# dev notes can go straight to /projects/acme/slop/example-repo/ipc-updates/
```

Review a PR branch, then clean up but keep the branch and your notes:

```sh
cd /projects/acme/example-repo
slop open origin/fix-parser
cd ../worktrees/example-repo/fix-parser
# ... review, jot review-notes.md ...
slop close --slop-untracked
cd /projects/acme/example-repo
# notes now at /projects/acme/slop/example-repo/fix-parser/review-notes.md
```

Get dev-only files out of the way before committing:

```sh
cd /projects/acme/worktrees/example-repo/ipc-updates
slop mv --untracked            # everything untracked
slop mv scripts/probe.lua      # or specific paths
```
