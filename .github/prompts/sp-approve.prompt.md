---
mode: agent
tools:
  - runInTerminal
  - terminalLastCommand
description: Approve a Superpowers stage and advance the flow to the next stage
---

Approve a stage in the Superpowers issue flow and advance to the next stage.

If the user has not specified an issue number and/or stage, ask for the missing values.

Valid stages: `goal`, `research`, `plan`, `implement`, `test`, `verify`, `release`

Run the following command from the repository root (argument order is flexible):

```bash
python scripts/sp.py approve <stage> <issue> --apply
```

This will:
1. Mark the stage as approved in the local YAML state.
2. Post a `/sp approve <stage>` audit comment on the GitHub issue.
3. Advance the local state to the next stage.
4. Write the next stage artifact to `.superpowers/runs/`.
5. Post the next stage `SP_STAGE: <next-stage>-ready` comment to GitHub.

After running, report:
- The stage that was approved
- The new current stage
- The next action required (e.g., "Comment `/sp approve research` on the issue to continue")

**Before approving**, run `/sp-status` to confirm the current stage is correct.

**Dry-run mode** (no GitHub writes):

```bash
python scripts/sp.py approve <stage> <issue> --dry-run
```
