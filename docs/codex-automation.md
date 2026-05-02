# Codex Automation Setup

Create a Codex cron automation that runs the poller periodically.

Recommended schedule: every 30 minutes.

Workspace:

```text
E:\workspace\superpowers-issue-automation-mvp
```

Prompt:

```text
Run `python scripts/poll_superpowers_issues.py --repo AILatentspace1/superpowers-issue-automation-mvp --dry-run`.
Summarize any Superpowers issue-flow actions that are needed. Do not mutate GitHub unless the user explicitly asks for --apply.
```

Apply mode prompt, only after testing dry-run:

```text
Run `python scripts/poll_superpowers_issues.py --repo AILatentspace1/superpowers-issue-automation-mvp --apply`.
Report which issue labels/comments were changed and include any errors.
```

Why this exists:

- GitHub Actions handles immediate issue/PR events.
- Codex Automation is a periodic watchdog for missed events, stuck issues, and human-readable status summaries.
