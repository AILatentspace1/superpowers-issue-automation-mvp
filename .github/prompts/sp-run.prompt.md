---
mode: agent
tools:
  - runInTerminal
  - terminalLastCommand
description: Sync a Superpowers issue and post the stage audit comment to GitHub
---

Sync one GitHub issue through the Superpowers flow and post the current stage audit comment.

If the user has not specified an issue number, ask: "Which issue number?"

Run the following command from the repository root:

```bash
python scripts/sp.py run <issue> --apply
```

This will:
1. Fetch the issue from GitHub.
2. Initialize or update the local YAML state under `.superpowers/issues/`.
3. Write the current stage artifact to `.superpowers/runs/`.
4. Post a `SP_STAGE: <stage>-ready` audit comment on the GitHub issue (if not already posted).

After running, report the current stage and the path of the written artifact.

**Safety**: `--apply` posts comments to GitHub. If the user wants a preview without GitHub writes, use `/sp-dry-run` instead.
