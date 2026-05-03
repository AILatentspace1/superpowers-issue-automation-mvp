# Superpowers Issue Automation - GitHub Copilot Instructions

This repository is a local Codex/Copilot orchestrator for a 7-stage GitHub Issues development flow.

## Stage machine

```
goal -> research -> plan -> implement -> test -> verify -> release
```

Each stage writes a Markdown artifact under `.superpowers/runs/` and posts an audit comment to the GitHub issue. A human (or agent) approves by commenting `/sp approve <stage>` on the issue, or by running the local command below.

## Commands (scripts/sp.py)

The entry point for all orchestration is `scripts/sp.py`. It delegates to `scripts/local_superpowers_orchestrator.py`.

| Intent | Command |
|---|---|
| Show stage, approvals, artifacts | `python scripts/sp.py status <issue>` |
| Sync issue & post GitHub comment | `python scripts/sp.py run <issue> --apply` |
| Sync issue locally (no GitHub writes) | `python scripts/sp.py run <issue> --dry-run` |
| Approve stage & advance | `python scripts/sp.py approve <stage> <issue> --apply` |
| Approve locally only | `python scripts/sp.py approve <stage> <issue> --dry-run` |

Argument order for approve is flexible: `approve goal 12` and `approve 12 goal` are both accepted.

## Projects

A project is a short alias for a GitHub repository. Register once, use everywhere.

**Priority chain**: `--project <name>` > `--repo OWNER/REPO` > active project > default repo

| Intent | Command |
|---|---|
| Register a new project (auto-activates) | `python scripts/sp.py project create <name> --repo OWNER/REPO` |
| Switch active project | `python scripts/sp.py project use <name>` |
| List all projects | `python scripts/sp.py project list` |
| Use project alias for one command | `python scripts/sp.py --project <name> status <issue>` |

Once a project is active, all commands default to it — no flag needed:
```bash
python scripts/sp.py project use wam
python scripts/sp.py status 2        # uses wam automatically
python scripts/sp.py approve goal 2 --apply
```

Project alias files are stored in `.superpowers/projects/<name>.yaml` and **are committed** (config, not runtime state).
The active project pointer is stored in `.superpowers/current_project` (gitignored, local state).

### Registered projects

| Alias | Repo |
|---|---|
| `wam` | `AILatentspace1/wechat-article-maker` |
| `wam-2` | `AILatentspace1/wechat-article-maker-2` |
| `sp-test` | `AILatentspace1/superpowers-issue-automation-mvp` |

## Valid stages

`goal`, `research`, `plan`, `implement`, `test`, `verify`, `release`

## Default repository

`AILatentspace1/superpowers-issue-automation-mvp`

Override: `python scripts/sp.py --repo OWNER/REPO <command> ...`
Or use a project alias: `python scripts/sp.py --project wam <command> ...`

## State files (gitignored, do not commit)

- `.superpowers/issues/<owner>__<repo>__<issue>.yaml` - local YAML state
- `.superpowers/runs/<owner>__<repo>/issue-<n>/<stage>.md` - stage artifacts
- `.superpowers/current_project` - active project pointer

## Project files (committed config)

- `.superpowers/projects/<name>.yaml` - project alias registry

## Safety rules

- `--dry-run` never writes to GitHub; safe to run any time.
- `--apply` posts comments and advances stage; always confirm the current stage with `status` first.
- Never commit `.superpowers/issues/*.yaml` or `.superpowers/runs/**`.

## Prompt files (use in Copilot Chat with `/`)

- `/sp-issues` - list all GitHub issues for the active project
- `/sp-issues` - list all GitHub issues for the active project
- `/sp-status` - check current stage and approvals for an issue
- `/sp-run` - sync an issue and post the stage audit comment to GitHub
- `/sp-dry-run` - sync an issue locally without writing to GitHub
- `/sp-approve` - approve a stage and advance the flow
- `/sp-project-create` - register a new project alias
- `/sp-project-use` - switch the active project
- `/sp-project-list` - list all registered projects
- `/wam` - all of the above pre-configured for the `wechat-article-maker` project