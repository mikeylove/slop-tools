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

### Add Explicit Untracked Close Choices

Extend `slop close` with explicit choices for untracked files.

Current direction:

- Refuse tracked changes by default.
- Require an explicit choice for untracked files, such as `--slop-untracked` or
  `--discard-untracked`.

### Extend Workspace Open

Extend `slop open` beyond existing local branches.

Possible sources:

- Remote-tracking branches.
- Pull request refs.
- Pull request URLs.

Current constraint: local branches are the first supported source type.

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

### Extract Managed Workspace Layout

Shared worktree/slop layout logic now lives in `slop_tools/workspaces.py`.

### Add Local Branch Open

`slop open <branch>` opens an existing local branch in the managed worktree
layout.

### Introduce CLI Command Registry

CLI choices, metavar text, and dispatch now derive from a single command
registration point.

### Add Clean Workspace Close

`slop close` removes a clean managed worktree without requiring a merge check or
deleting the local branch.

## Rejected

No rejected items yet.

## Ignored

No ignored items yet.
