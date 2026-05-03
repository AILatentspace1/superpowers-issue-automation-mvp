#!/usr/bin/env python3
"""Short command wrapper for the local Superpowers issue orchestrator.

This is intentionally small: it translates human-friendly Codex command shapes
into the canonical `scripts/local_superpowers_orchestrator.py` CLI.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_REPO = "AILatentspace1/superpowers-issue-automation-mvp"
ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "scripts" / "local_superpowers_orchestrator.py"
PROJECTS_DIR = ROOT / ".superpowers" / "projects"
CURRENT_PROJECT_FILE = ROOT / ".superpowers" / "current_project"
STAGES = ["goal", "research", "plan", "implement", "test", "verify", "release"]


def run_orchestrator(args: list[str]) -> int:
    completed = subprocess.run([sys.executable, str(ORCHESTRATOR), *args], cwd=ROOT)
    return completed.returncode


def _gh(cmd: list[str]) -> subprocess.CompletedProcess:
    """Run a gh CLI command, return CompletedProcess. Never raises."""
    return subprocess.run(["gh", *cmd], text=True, encoding="utf-8", capture_output=True)


def _create_github_project(name: str, owner: str, repo: str) -> tuple[int, str]:
    """Create a GitHub Project v2, link the repo, add Stage field, attempt Board view.

    Returns (project_number, project_url). Raises SystemExit on critical failure.
    """
    title = f"Superpowers: {name}"

    # 1. Create project
    r = _gh(["project", "create", "--owner", owner, "--title", title, "--format", "json"])
    if r.returncode != 0:
        raise SystemExit(f"gh project create failed:\n{r.stderr.strip()}")
    data = json.loads(r.stdout)
    number: int = data["number"]
    url: str = data["url"]
    print(f"  GitHub Project created: {url}")

    # 2. Link repo
    r = _gh(["project", "link", str(number), "--owner", owner, "--repo", repo])
    if r.returncode != 0:
        print(f"  Warning: could not link repo ({r.stderr.strip()})", file=sys.stderr)
    else:
        print(f"  Repo linked: {repo}")

    # 3. Create Stage single-select field
    stage_cmd = [
        "project", "field-create", str(number),
        "--owner", owner,
        "--name", "Stage",
        "--data-type", "SINGLE_SELECT",
    ]
    for s in STAGES:
        stage_cmd += ["--single-select-option", s]
    r = _gh(stage_cmd)
    if r.returncode != 0:
        print(f"  Warning: could not create Stage field ({r.stderr.strip()})", file=sys.stderr)
    else:
        print(f"  Stage field created ({', '.join(STAGES)})")

    # 4. Board view via GraphQL (best-effort)
    r = _gh(["project", "view", str(number), "--owner", owner, "--format", "json"])
    if r.returncode == 0:
        try:
            proj_data = json.loads(r.stdout)
            proj_id = proj_data.get("id", "")
            if proj_id:
                gql = (
                    'mutation { createProjectV2View(input: {'
                    'projectId: \\"' + proj_id + '\\"'
                    ', name: \\"Board by Stage\\"'
                    ', layout: BOARD_LAYOUT'
                    '}) { projectV2View { id name } } }'
                )
                r2 = _gh(["api", "graphql", "-f", f"query={gql}"])
                if r2.returncode == 0:
                    print("  Board view 'Board by Stage' created")
                else:
                    print("  Note: Board view could not be created via API (configure in GitHub UI)")
        except Exception:
            print("  Note: Board view setup skipped (configure in GitHub UI)")

    return number, url


def parse_approve_args(values: list[str]) -> tuple[str, int]:
    if len(values) != 2:
        raise SystemExit("approve expects two arguments: <stage> <issue> or <issue> <stage>")
    first, second = values
    if first in STAGES and second.isdigit():
        return first, int(second)
    if second in STAGES and first.isdigit():
        return second, int(first)
    raise SystemExit(
        "approve expects one stage and one issue number. "
        f"Stages: {', '.join(sorted(STAGES))}"
    )


def load_project(name: str) -> str:
    """Load a project by name and return its repo (owner/name)."""
    path = PROJECTS_DIR / f"{name}.yaml"
    if not path.exists():
        raise SystemExit(
            f"Project {name!r} not found. "
            f"Create it with: python scripts/sp.py project create {name} --repo OWNER/REPO"
        )
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise SystemExit("PyYAML is required. Install with: pip install PyYAML") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    repo = data.get("repo", "").strip()
    if not repo or "/" not in repo:
        raise SystemExit(f"Project {name!r} has invalid or missing 'repo' field in {path}")
    return repo


def get_active_project() -> str | None:
    """Return the active project name from .superpowers/current_project, or None."""
    if CURRENT_PROJECT_FILE.exists():
        name = CURRENT_PROJECT_FILE.read_text(encoding="utf-8").strip()
        if name:
            return name
    return None


def set_active_project(name: str) -> None:
    """Write the active project name to .superpowers/current_project."""
    CURRENT_PROJECT_FILE.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_PROJECT_FILE.write_text(name, encoding="utf-8")


def _resolve_repo(args: argparse.Namespace) -> str:
    """Resolve repo: --project > --repo (if explicitly set) > active project > DEFAULT_REPO."""
    project = getattr(args, "project", None)
    if project:
        return load_project(project)
    # If --repo was explicitly provided (not the default), use it
    repo = getattr(args, "repo", None)
    if repo and repo != DEFAULT_REPO:
        return repo
    # Fall back to active project
    active = get_active_project()
    if active:
        return load_project(active)
    return repo or DEFAULT_REPO


def _save_project(
    name: str,
    repo: str,
    description: str,
    github_project_number: int = 0,
    github_project_url: str = "",
) -> Path:
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    path = PROJECTS_DIR / f"{name}.yaml"
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        'schema_version: "1"',
        f"name: {json.dumps(name)}",
        f"repo: {json.dumps(repo)}",
        f"description: {json.dumps(description)}",
        f"created_at: {json.dumps(created_at)}",
    ]
    if github_project_number:
        lines.append(f"github_project_number: {github_project_number}")
    if github_project_url:
        lines.append(f"github_project_url: {json.dumps(github_project_url)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def cmd_project(args: argparse.Namespace) -> int:
    if args.project_command == "create":
        name = args.name
        if not all(c.isalnum() or c in "-_" for c in name):
            raise SystemExit(f"Project name {name!r} must contain only letters, digits, hyphens, underscores")
        if "/" not in args.repo:
            raise SystemExit("--repo must be owner/name")
        owner = args.repo.split("/")[0]
        gh_number, gh_url = 0, ""
        if not getattr(args, "no_github_project", False):
            print(f"Creating GitHub Project for {name!r}...")
            try:
                gh_number, gh_url = _create_github_project(name, owner, args.repo)
            except SystemExit as exc:
                print(f"  Warning: {exc}", file=sys.stderr)
        path = _save_project(name, args.repo, args.description or "", gh_number, gh_url)
        set_active_project(name)
        print(f"Created project {name!r} -> {args.repo}")
        print(f"  {path.relative_to(ROOT)}")
        if gh_url:
            print(f"  GitHub Project: {gh_url}")
        print(f"  Active project set to: {name!r}")
        return 0

    if args.project_command == "use":
        name = args.name
        # Validate the project exists
        load_project(name)
        set_active_project(name)
        print(f"Active project set to: {name!r}")
        return 0

    if args.project_command == "list":
        active = get_active_project()
        if not PROJECTS_DIR.exists():
            print("No projects registered yet.")
            print("  Create one with: python scripts/sp.py project create <name> --repo OWNER/REPO")
            return 0
        projects = sorted(PROJECTS_DIR.glob("*.yaml"))
        if not projects:
            print("No projects registered yet.")
            return 0
        try:
            import yaml  # type: ignore
            for p in projects:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                desc = data.get("description", "")
                suffix = f"  # {desc}" if desc else ""
                name = data.get("name", p.stem)
                marker = "* " if name == active else "  "
                gh_proj = data.get("github_project_url", "")
                proj_suffix = f"  [Project: {gh_proj}]" if gh_proj else ""
                print(f"{marker}{name:<20} -> {data.get('repo', '?')}{suffix}{proj_suffix}")
        except ImportError:
            for p in projects:
                marker = "* " if p.stem == active else "  "
                print(f"{marker}{p.stem}")
        if active:
            print(f"\n(* = active project; use `project use <name>` to switch)")
        return 0

    return 2


def _next_stage(stage: str) -> "str | None":
    try:
        idx = STAGES.index(stage)
    except ValueError:
        return None
    return STAGES[idx + 1] if idx + 1 < len(STAGES) else None


def _project_flag(args_project: "str | None", repo: str) -> list:
    if args_project:
        return ["--project", args_project]
    active = get_active_project()
    if active:
        return ["--project", active]
    if repo and repo != DEFAULT_REPO:
        return ["--repo", repo]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Short /sp command wrapper for local Superpowers flow")
    repo_group = parser.add_mutually_exclusive_group()
    repo_group.add_argument("--repo", default=DEFAULT_REPO, help=f"owner/name; default: {DEFAULT_REPO}")
    repo_group.add_argument("--project", metavar="NAME", help="project alias defined in .superpowers/projects/")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show current local/GitHub stage status")
    status.add_argument("issue", type=int)

    run = subparsers.add_parser("run", help="sync one issue or discover issues")
    run.add_argument("issue", type=int, nargs="?")
    run.add_argument("--discover-label", default="sp:local-flow")
    run_group = run.add_mutually_exclusive_group()
    run_group.add_argument("--apply", action="store_true", help="post GitHub audit/stage comments")
    run_group.add_argument("--dry-run", action="store_true", help="do not mutate GitHub; default for run")

    approve = subparsers.add_parser("approve", help="approve a stage and advance the flow")
    approve.add_argument("values", nargs=2, metavar="ARG", help="<stage> <issue> or <issue> <stage>")
    approve_group = approve.add_mutually_exclusive_group()
    approve_group.add_argument("--apply", action="store_true", help="post GitHub audit/stage comments; default for approve")
    approve_group.add_argument("--dry-run", action="store_true", help="update local YAML only; do not mutate GitHub")
    approve.add_argument("--no-audit-comment", action="store_true")

    project_cmd = subparsers.add_parser("project", help="manage project aliases")
    project_sub = project_cmd.add_subparsers(dest="project_command", required=True)

    proj_create = project_sub.add_parser("create", help="register a new project alias")
    proj_create.add_argument("name", help="short alias, e.g. wam")
    proj_create.add_argument("--repo", required=True, help="owner/name of the GitHub repository")
    proj_create.add_argument("--description", default="", help="optional description")
    proj_create.add_argument(
        "--no-github-project", action="store_true",
        help="skip creating the GitHub Project v2 (offline / dry-run)",
    )

    project_sub.add_parser("list", help="list all registered project aliases")

    proj_use = project_sub.add_parser("use", help="set the active project (persisted locally)")
    proj_use.add_argument("name", help="project alias to activate")

    issues_cmd = subparsers.add_parser("issues", help="list GitHub issues for the active project")
    issues_cmd.add_argument("--state", default="open", choices=["open", "closed", "all"], help="issue state filter (default: open)")
    issues_cmd.add_argument("--limit", type=int, default=30, help="max number of issues to return (default: 30)")
    issues_cmd.add_argument("--label", default="", help="filter by label")

    args = parser.parse_args(argv)

    if args.command == "project":
        return cmd_project(args)

    repo = _resolve_repo(args)

    if args.command == "status":
        return run_orchestrator(["status", "--repo", repo, "--issue", str(args.issue)])

    if args.command == "run":
        cmd = ["run", "--repo", repo, "--discover-label", args.discover_label]
        if args.issue is not None:
            cmd.extend(["--issue", str(args.issue)])
        if args.apply:
            cmd.append("--apply")
        else:
            cmd.append("--dry-run")
        return run_orchestrator(cmd)

    if args.command == "approve":
        stage, issue = parse_approve_args(args.values)
        cmd = ["approve", "--repo", repo, "--issue", str(issue), "--stage", stage]
        if not args.dry_run:
            cmd.append("--apply")
        if args.no_audit_comment:
            cmd.append("--no-audit-comment")
        rc = run_orchestrator(cmd)
        if rc == 0 and not args.dry_run:
            next_s = _next_stage(stage)
            flags = _project_flag(getattr(args, "project", None), repo)
            flag_str = (" ".join(flags) + " ") if flags else ""
            print()
            if next_s:
                print("Next steps:")
                print(f"  Copilot Chat : /sp-run {issue}  then  /sp-approve {next_s} {issue}")
                print(f"  Codex        : /sp run {issue}  then  /sp approve {next_s} {issue}")
                print(f"  Terminal     : python scripts/sp.py {flag_str}run {issue} --apply")
            else:
                print("All stages complete. Flow is done.")
        return rc

    if args.command == "issues":
        import json as _json
        import subprocess as _sp
        gh_cmd = ["gh", "issue", "list", "--repo", repo,
                  "--state", args.state, "--limit", str(args.limit),
                  "--json", "number,title,state,labels,assignees,createdAt"]
        if args.label:
            gh_cmd.extend(["--label", args.label])
        r = _sp.run(gh_cmd, text=True, encoding="utf-8", capture_output=True)
        if r.returncode != 0:
            print(f"Error: {r.stderr.strip()}", file=sys.stderr)
            return r.returncode
        issues = _json.loads(r.stdout or "[]")
        if not issues:
            print(f"No {args.state} issues found for {repo}")
            return 0
        print(f"{len(issues)} {args.state} issue(s) for {repo}:\n")
        for iss in issues:
            labels = ", ".join(l["name"] for l in iss.get("labels", []))
            assignees = ", ".join(a["login"] for a in iss.get("assignees", []))
            label_str = f"  [{labels}]" if labels else ""
            assignee_str = f"  @{assignees}" if assignees else ""
            print(f"  #{iss['number']:<5} {iss['title']}{label_str}{assignee_str}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())