# /sp-project-create

Register a new project alias for a GitHub repository.

## Usage

```
/sp-project-create <name> <OWNER/REPO> [description]
```

## Steps

1. Ask for missing values if not provided:
   - Alias name (short, e.g. `myapp`)
   - GitHub repo in `OWNER/REPO` format
   - Optional description

2. Run:

```bash
python scripts/sp.py project create <name> --repo <OWNER/REPO> [--description "<description>"]
```

3. Verify with:

```bash
python scripts/sp.py project list
```

4. Remind user to commit `.superpowers/projects/<name>.yaml` — it is config, not runtime state.

## Notes

- Project files live in `.superpowers/projects/<name>.yaml` and are committed to git.
- After registration, use `--project <name>` with any sp command instead of `--repo OWNER/REPO`.
- `--project` and `--repo` are mutually exclusive flags.