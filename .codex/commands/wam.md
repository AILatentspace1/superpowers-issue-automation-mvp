# /wam Codex command

Use this command spec when the user types `/wam ...` in Codex while working in this repository.

Target project: `wam` (alias for `AILatentspace1/wechat-article-maker`)

## Command mappings

- `/wam status <issue>`
  - Run: `python scripts/sp.py --project wam status <issue>`

- `/wam run <issue>`
  - Run: `python scripts/sp.py --project wam run <issue> --apply`

- `/wam dry-run <issue>`
  - Run: `python scripts/sp.py --project wam run <issue> --dry-run`

- `/wam approve <stage> <issue>`
  - Run: `python scripts/sp.py --project wam approve <stage> <issue> --apply`

- `/wam approve <issue> <stage>`
  - Run: `python scripts/sp.py --project wam approve <issue> <stage> --apply`

## Valid stages

`goal`, `research`, `plan`, `implement`, `test`, `verify`, `release`n
## Safety notes

- `status` and `dry-run` do not mutate GitHub.
- `run` and `approve` post comments to GitHub - confirm stage with `status` first.
- Do not commit `.superpowers/issues/*.yaml` or `.superpowers/runs/**`.
