---
mode: agent
tools:
  - runInTerminal
  - terminalLastCommand
description: Show current stage, approvals, and artifacts for a Superpowers issue
---

Show the current Superpowers flow status for a GitHub issue.

If the user has not specified an issue number, ask: "Which issue number?"

Run the following command from the repository root, substituting the issue number:

```bash
python scripts/sp.py status <issue>
```

Report back:
- Current stage
- Which stages are approved
- Artifact file paths (if any)
- The GitHub issue URL

Do not modify any files. This command is read-only (it may initialize local YAML state if the issue has never been synced before, but it does not post to GitHub).
