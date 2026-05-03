---
mode: agent
tools:
  - runInTerminal
description: Register a new project alias for a GitHub repository
---

Register a new Superpowers project alias so you can use `--project <name>` instead of `--repo OWNER/REPO` for all future commands.

If the user has not provided all required values, ask:
1. "What short alias name for this project?" (e.g. `myapp`)
2. "What is the GitHub repo? (format: OWNER/REPO)"
3. "Optional description?" (can be left blank)

Then run from the repository root:

```bash
python scripts/sp.py project create <name> --repo <OWNER/REPO> [--description "<description>"]
```

After success, confirm:
- The alias name
- The repo it points to
- Where the project file was saved (`.superpowers/projects/<name>.yaml`)
- Remind the user to **commit** this file — it is config, not runtime state.

To verify, run:

```bash
python scripts/sp.py project list
```