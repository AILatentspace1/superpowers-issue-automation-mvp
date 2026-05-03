---
mode: agent
tools:
  - runInTerminal
description: Switch the active project so all subsequent sp commands default to it
---

Switch the active Superpowers project. Once set, all commands (`status`, `run`, `approve`) will use this project by default — no need to type `--project <name>` every time.

If the user has not specified a project name, first list available projects:

```bash
python scripts/sp.py project list
```

Then ask: "Which project do you want to activate?"

Run:

```bash
python scripts/sp.py project use <name>
```

Confirm which project is now active and what repo it points to.

**Priority chain**: `--project <name>` > `--repo OWNER/REPO` > active project > default repo