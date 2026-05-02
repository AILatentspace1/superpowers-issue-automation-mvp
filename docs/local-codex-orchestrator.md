# Local Codex Superpowers Orchestrator

This is the recommended direction when you want reliable Superpowers execution:

```text
GitHub Issue = input, approvals, audit log
Local YAML = source-of-truth state machine
Local Codex = orchestrator and executor
Codex Automations = periodic watchdog / continuation runner
```

## State files

State is stored under:

```text
.superpowers/issues/<owner>__<repo>__<issue>.yaml
.superpowers/runs/<owner>__<repo>/issue-<n>/<stage>.md
```

Example state:

```yaml
schema_version: "1"
repo: "AILatentspace1/superpowers-issue-automation-mvp"
issue: "9"
stage: "research"
status: "pending"
approvals:
  goal: "true"
  research: "false"
artifacts:
  goal: ".superpowers/runs/.../goal.md"
```

## Stages

```text
goal -> research -> plan -> implement -> test -> verify -> release
```

Each stage writes an artifact and posts a GitHub issue comment with:

```text
SP_STAGE: <stage>-ready
```

A human approves the current stage by commenting on the issue:

```text
/sp approve goal
/sp approve research
/sp approve plan
/sp approve implement
/sp approve test
/sp approve verify
```

## Commands

Dry-run a single issue:

```bash
python scripts/local_superpowers_orchestrator.py \
  --repo AILatentspace1/superpowers-issue-automation-mvp \
  --issue 9 \
  --dry-run
```

Apply comments for a single issue:

```bash
python scripts/local_superpowers_orchestrator.py \
  --repo AILatentspace1/superpowers-issue-automation-mvp \
  --issue 9 \
  --apply
```

Discover open issues by label:

```bash
python scripts/local_superpowers_orchestrator.py \
  --repo AILatentspace1/superpowers-issue-automation-mvp \
  --discover-label sp:local-flow \
  --apply
```

## Why local is easier than GitHub Web Copilot

- The state machine is explicit and inspectable.
- Codex can read local files, edit code, run tests, inspect logs, and push PRs.
- Stage transitions are deterministic and stored in YAML.
- GitHub remains the collaboration/audit surface.
- Codex Automations can continue the flow without relying on opaque Copilot sessions.
