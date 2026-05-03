# /sp-project-list

List all registered project aliases and show which is currently active.

## Usage

```
/sp-project-list
```

## Steps

Run:

```bash
python scripts/sp.py project list
```

Report all aliases, their repos, and which is active (`*`).
To switch: `python scripts/sp.py project use <name>`