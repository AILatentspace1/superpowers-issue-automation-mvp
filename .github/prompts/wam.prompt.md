---
mode: agent
tools:
  - runInTerminal
  - terminalLastCommand
description: >-
  Superpowers flow commands for wechat-article-maker project (alias: wam).
  Wraps sp.py with --project wam pre-set.
---

# Superpowers commands for `wechat-article-maker` (project: wam)

This prompt wraps `scripts/sp.py` with `--project wam` pre-set.
`wam` is a registered project alias for `AILatentspace1/wechat-article-maker`.

## Usage

Tell me which sub-command to run and the issue number (and stage if approving):

- **status `<issue>`** - show current stage, approvals, artifacts
- **run `<issue>`** - sync issue and post stage audit comment to GitHub
- **dry-run `<issue>`** - sync locally without writing to GitHub
- **approve `<stage>` `<issue>`** - approve stage and advance to next

Valid stages: `goal`, `research`, `plan`, `implement`, `test`, `verify`, `release`

## Command mappings

| Intent | Command |
|---|---|
| status | `python scripts/sp.py --project wam status <issue>` |
| run | `python scripts/sp.py --project wam run <issue> --apply` |
| dry-run | `python scripts/sp.py --project wam run <issue> --dry-run` |
| approve | `python scripts/sp.py --project wam approve <stage> <issue> --apply` |

Run all commands from the `e:\workspace\superpowers-issue-automation-mvp` repository root.

If the user has not specified an issue number, ask: "Which issue number?"
If approving and no stage specified, first run status to show current stage, then ask: "Which stage to approve?"

**Safety**: `run` and `approve` post comments to GitHub. Use `dry-run` to preview without GitHub writes.