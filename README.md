# Superpowers Issue Automation MVP

Minimal GitHub Issues orchestrator for a Superpowers-style software development flow.

This repository demonstrates two layers:

1. **GitHub Actions event layer** — reacts immediately to issue labels and PR check failures.
2. **Codex Automation poller layer** — can run periodically to find stuck issues and print/optionally apply next actions.

The MVP uses GitHub issue labels as the state machine and comments to trigger Copilot/custom code agents.


## Local Codex orchestrator

The recommended reliable path is now **local Codex + GitHub Issues + YAML state**.

Run a local stage sync:

```bash
python scripts/local_superpowers_orchestrator.py --repo AILatentspace1/superpowers-issue-automation-mvp --issue 9 --dry-run
```

State lives in `.superpowers/issues/*.yaml`; artifacts live in `.superpowers/runs/`. GitHub issues remain the input, approval, and audit surface. See [`docs/local-codex-orchestrator.md`](docs/local-codex-orchestrator.md).

## Flow

```text
Issue opened
  -> sp:needs-design
  -> comment for superpowers-product-planner
User adds sp:design-approved
  -> sp:needs-plan
  -> comment for superpowers-implementation-planner
User adds sp:plan-approved
  -> sp:needs-implementation
  -> comment for superpowers-implementer
PR CI failure
  -> comment for superpowers-debugger
PR CI success
  -> comment for superpowers-code-reviewer / release-captain
```

## Required labels

Run:

```bash
gh label create "sp:needs-design" --color 5319E7 --description "Superpowers: design needed"
gh label create "sp:design-approved" --color 0E8A16 --description "Superpowers: design approved by human"
gh label create "sp:needs-plan" --color 5319E7 --description "Superpowers: implementation plan needed"
gh label create "sp:plan-approved" --color 0E8A16 --description "Superpowers: implementation plan approved by human"
gh label create "sp:needs-implementation" --color FBCA04 --description "Superpowers: implementation needed"
gh label create "sp:needs-debug" --color D93F0B --description "Superpowers: debugger needed"
gh label create "sp:needs-code-review" --color 1D76DB --description "Superpowers: code review needed"
gh label create "sp:needs-release-check" --color 1D76DB --description "Superpowers: release verification needed"
gh label create "sp:blocked" --color B60205 --description "Superpowers: blocked"
gh label create "sp:done" --color 0E8A16 --description "Superpowers: done"
```


## Copilot execution setup

GitHub Actions comments from `github-actions[bot]` are useful audit markers, but they do **not** reliably start Copilot coding agent work. To start Copilot programmatically, this MVP uses the official Copilot issue assignment API.

Create a repository secret named `COPILOT_ASSIGN_PAT`:

```bash
gh secret set COPILOT_ASSIGN_PAT --repo AILatentspace1/superpowers-issue-automation-mvp --body "$(gh auth token)"
```

The token must be a user token that can assign Copilot coding agent. GitHub's default `GITHUB_TOKEN` is not sufficient for Copilot assignment.

When `sp:plan-approved` is added to a sample-flow issue, the workflow assigns `copilot-swe-agent` with `customAgent: superpowers-implementer` and implementation instructions.

## Usage

1. Create an issue using the Superpowers feature request template.
2. The workflow adds `sp:needs-design` and comments to invoke the planner agent.
3. Review the planner output, then add `sp:design-approved`.
4. Review the implementation plan, then add `sp:plan-approved`.
5. Copilot/custom agent creates a PR.
6. PR workflows trigger debugger/reviewer/release-captain comments based on check results.

## Codex Automation poller

For a periodic Codex Automation, use prompt like:

```text
In E:\workspace\superpowers-issue-automation-mvp, run:
python scripts/poll_superpowers_issues.py --repo AILatentspace1/superpowers-issue-automation-mvp --dry-run
Summarize stuck issues and recommended next actions. Do not mutate GitHub unless explicitly requested.
```

To apply comments/labels manually:

```bash
python scripts/poll_superpowers_issues.py --repo AILatentspace1/superpowers-issue-automation-mvp --apply
```

## Safety

- Human approval labels are required between design -> plan and plan -> implementation.
- The planner prompt asks for planning-only output.
- The automation is label-driven and idempotent: it checks for existing marker comments before posting again.
