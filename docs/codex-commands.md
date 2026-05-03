# Codex commands

This repository defines a local Superpowers command surface for Codex sessions.

## `/sp`

The command spec lives at `.codex/commands/sp.md`. It maps short human commands to the executable wrapper `scripts/sp.py`, which delegates to `scripts/local_superpowers_orchestrator.py`.

Examples:

```bash
python scripts/sp.py status 12
python scripts/sp.py run 12 --dry-run
python scripts/sp.py run 12 --apply
python scripts/sp.py approve goal 12 --apply
python scripts/sp.py approve 12 research --dry-run
```

In Codex chat, use these forms:

```text
/sp status 12
/sp run 12
/sp dry-run 12
/sp approve goal 12
```

The intended Codex behavior is to translate those chat commands into the matching `python scripts/sp.py ...` invocation from the repository root.

## Default repo

`scripts/sp.py` defaults to:

```text
AILatentspace1/superpowers-issue-automation-mvp
```

Override it when controlling another GitHub repository:

```bash
python scripts/sp.py --repo OWNER/REPO status 123
```
