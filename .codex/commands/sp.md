# /sp Codex command

Use this command spec when the user types `/sp ...` in Codex while working in this repository.

Default repository:

```text
AILatentspace1/superpowers-issue-automation-mvp
```n
## Command mappings

- `/sp status <issue>`
  - Run: `python scripts/sp.py status <issue>`
  - Purpose: show current local YAML state, GitHub URL, stage, approvals, and artifacts.

- `/sp run <issue>`
  - Run: `python scripts/sp.py run <issue> --apply`
  - Purpose: sync one issue, create/update the current stage artifact, and post the stage audit comment to GitHub.

- `/sp dry-run <issue>`
  - Run: `python scripts/sp.py run <issue> --dry-run`
  - Purpose: sync one issue locally without mutating GitHub comments.

- `/sp approve <stage> <issue>`
  - Run: `python scripts/sp.py approve <stage> <issue> --apply`
  - Purpose: approve the current or named stage, write the local YAML approval, post a GitHub audit comment, and advance to the next stage.

- `/sp approve <issue> <stage>`
  - Run: `python scripts/sp.py approve <issue> <stage> --apply`
  - Purpose: same as above; reversed argument order is accepted.

## Projects

- `/sp project create <name> --repo OWNER/REPO`
  - Run: `python scripts/sp.py project create <name> --repo OWNER/REPO`
  - Purpose: register a new project alias stored in `.superpowers/projects/<name>.yaml`.

- `/sp project list`
  - Run: `python scripts/sp.py project list`
  - Purpose: list all registered project aliases.

- `/sp --project <name> status <issue>`
  - Run: `python scripts/sp.py --project <name> status <issue>`
  - Purpose: run any command against a project alias instead of typing the full repo path.

## Valid stages

`goal`, `research`, `plan`, `implement`, `test`, `verify`, `release`n
## Safety notes

- `status` is read-only except that the underlying orchestrator may initialize missing local state.
- `run --dry-run` does not mutate GitHub.
- `approve --dry-run` updates local YAML but does not post GitHub comments.
- Do not commit `.superpowers/issues/*.yaml` or `.superpowers/runs/**`; they are local runtime state.
- `.superpowers/projects/*.yaml` ARE committed; they are config, not runtime state.
