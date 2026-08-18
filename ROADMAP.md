# Roadmap

This document tracks planned, completed, rejected, and intentionally ignored
ideas for `slop-tools`. It is a design ledger, not a promise that every open
item will ship.

## Status

- `open`: still under consideration or not started.
- `in-progress`: actively being worked on.
- `done`: completed in the codebase.
- `rejected`: considered and decided against.
- `ignored`: intentionally left alone unless new information changes the tradeoff.

## Open

### Extend Workspace Open To Pull Requests

Extend `slop open` beyond existing local and remote-tracking branches.

Possible sources:

- Pull request refs.
- Pull request URLs.

### Restructure README

Consider reshaping `README.md` around:

- Overview.
- Workflows.
- Command index.
- Installation and implementation details.

The goal is to make the user-facing workflow model clearer as the command set
grows.

### Explore Command Package Auto-Registration

Consider moving command modules into a dedicated package where each module
exports a consistent `COMMAND` symbol.

Possible direction:

- Scan only the dedicated command package.
- Fail loudly if a command module exports an invalid shape.
- Keep legacy executable aliases separate from subcommand discovery.
- Preserve intentional command ordering rather than relying on filesystem scan
  order.

## Done

### Pre-Create Slop Directory In Worktree Lifecycles

`slop init` and `slop open` now create the matching `slop/<repository>/<branch>`
directory alongside the worktree, so dev-only files can be placed there from
the start without hand-computing the mapping. `slop close` and `slop teardown`
prune the slop directory (and empty parents, up to the slop root) when it is
still empty, so the slop tree keeps holding only branches that actually
preserved something.

An opt-in `--slop` flag was considered and rejected in favor of default-on
creation paired with prune-on-remove. All four lifecycle commands gained
`--slop-name` for parity with `slop mv`, and `close`/`teardown` now forward
`--worktrees-name`/`--slop-name` to their internal `slop mv --untracked` step.

### Extract Managed Workspace Layout

Shared worktree/slop layout logic now lives in `slop_tools/workspaces.py`.

### Add Local Branch Open

`slop open <branch>` opens an existing local branch in the managed worktree
layout.

### Add Remote Tracking Branch Open

`slop open <remote>/<branch>` creates a local tracking branch and opens it in
the managed worktree layout.

### Introduce CLI Command Registry

CLI choices, metavar text, and dispatch now derive from a single command
registration point.

### Add Clean Workspace Close

`slop close` removes a clean managed worktree without requiring a merge check or
deleting the local branch.

### Add Slop Untracked Close

`slop close --slop-untracked` moves untracked files to the matching `slop` tree
before removing the managed worktree.

### Add Discard Untracked Close

`slop close --discard-untracked` deletes untracked files before removing the
managed worktree. Tracked changes still block close.

## Rejected

No rejected items yet.

## Ignored

No ignored items yet.
