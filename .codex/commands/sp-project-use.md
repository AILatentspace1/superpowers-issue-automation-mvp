# /sp-project-use

Switch the active project. Once set, all `status`, `run`, `approve` commands default to it without needing `--project <name>`.

## Usage

```
/sp-project-use [name]
```

## Steps

1. If no name given, run `python scripts/sp.py project list` and ask which to activate.

2. Run:

```bash
python scripts/sp.py project use <name>
```

3. Confirm the active project name and its repo.

## Notes

- Active project is stored in `.superpowers/current_project` (gitignored).
- Priority: `--project` > `--repo` > active project > default repo.
- `project create` automatically activates the new project.