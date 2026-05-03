---
mode: agent
tools:
  - runInTerminal
description: List all registered project aliases and show which one is active
---

List all registered Superpowers project aliases.

Run:

```bash
python scripts/sp.py project list
```

Report:
- All registered aliases and the GitHub repos they point to
- Which project is currently active (marked with `*`)
- How to switch: `python scripts/sp.py project use <name>`