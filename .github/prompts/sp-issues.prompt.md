---
mode: agent
tools:
  - runInTerminal
description: List all GitHub issues for the active Superpowers project
---

List GitHub issues for the active Superpowers project.

Run:

```bash
python scripts/sp.py issues
```

Optional flags the user may request:
- `--state open|closed|all` (default: open)
- `--limit N` (default: 30)
- `--label <label>` filter by label
- `--project <name>` override active project

Report:
- How many issues were found and for which repo
- Each issue: number, title, labels, assignees
- Remind the user they can run `python scripts/sp.py status <issue>` to inspect a specific issue
