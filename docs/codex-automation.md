# Codex Automation Setup

Create a Codex cron automation that runs the local orchestrator periodically.

Recommended schedule: every 30 minutes.

Workspace:

```text
E:\workspace\superpowers-issue-automation-mvp
```

Recommended dry-run prompt:

```text
Run `python scripts/local_superpowers_orchestrator.py --repo AILatentspace1/superpowers-issue-automation-mvp --discover-label sp:local-flow --dry-run`.
Summarize which GitHub issues have pending Superpowers stage actions and which local YAML/artifacts would be updated. Do not mutate GitHub unless explicitly requested.
```

Apply mode prompt, only after testing dry-run:

```text
Run `python scripts/local_superpowers_orchestrator.py --repo AILatentspace1/superpowers-issue-automation-mvp --discover-label sp:local-flow --apply`.
Report which local state files, artifacts, GitHub comments, and labels changed.
```

The older `poll_superpowers_issues.py` script is retained as a simple label/comment demo. The preferred workflow is `local_superpowers_orchestrator.py`, because it stores durable state in local YAML and can be resumed by Codex Automations.
