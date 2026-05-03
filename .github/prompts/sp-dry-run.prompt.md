---
mode: agent
tools:
  - runInTerminal
  - terminalLastCommand
description: Sync a Superpowers issue locally without writing to GitHub
---

Sync one GitHub issue through the Superpowers flow **without posting any comments to GitHub**.

If the user has not specified an issue number, ask: "Which issue number?"

Run the following command from the repository root:

```bash
python scripts/sp.py run <issue> --dry-run
```

This will:
1. Fetch the issue from GitHub (read-only).
2. Initialize or update the local YAML state under `.superpowers/issues/`.
3. Write the current stage artifact to `.superpowers/runs/`.
4. Print what comment *would* be posted — but not post it.

After running, report:
- The current stage
- The artifact path that was written
- What the pending GitHub comment would say

**Safety**: This command never writes to GitHub. It is safe to run at any time to preview the next action.
