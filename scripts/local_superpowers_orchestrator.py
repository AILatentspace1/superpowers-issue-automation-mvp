#!/usr/bin/env python3
"""Local Codex Superpowers orchestrator for GitHub Issues.

The source of truth is local YAML state under `.superpowers/issues/`.
GitHub Issues are used as input, approval surface, and audit log.

This script intentionally does not call an LLM. It prepares deterministic stage
artifacts and comments. A Codex automation can run it periodically, and a human
(or a separate Codex session) can implement approved plans locally.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / ".superpowers" / "issues"
RUNS_DIR = ROOT / ".superpowers" / "runs"

STAGES = ["goal", "research", "plan", "implement", "test", "verify", "release"]
APPROVAL_COMMENT_RE = re.compile(r"^/sp\s+approve\s+(goal|research|plan|implement|test|verify|release)\b", re.I)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True)
    if check and completed.returncode != 0:
        raise RuntimeError(
            "Command failed: " + " ".join(cmd) + "\n"
            + "STDOUT:\n" + completed.stdout + "\n"
            + "STDERR:\n" + completed.stderr
        )
    return completed


def gh_json(args: list[str]) -> Any:
    completed = run(["gh", *args])
    return json.loads(completed.stdout)


def slug_repo(repo: str) -> str:
    return repo.replace("/", "__")


def state_path(repo: str, issue: int) -> Path:
    return STATE_DIR / f"{slug_repo(repo)}__{issue}.yaml"


def run_dir(repo: str, issue: int) -> Path:
    return RUNS_DIR / slug_repo(repo) / f"issue-{issue}"


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def dump_yaml(data: dict[str, Any]) -> str:
    # Tiny deterministic YAML writer for the simple state schema we own.
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for k2, v2 in value.items():
                if isinstance(v2, bool):
                    vv = "true" if v2 else "false"
                elif v2 is None:
                    vv = "null"
                else:
                    vv = yaml_quote(str(v2))
                lines.append(f"  {k2}: {vv}")
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {yaml_quote(str(item))}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{key}: null")
        else:
            lines.append(f"{key}: {yaml_quote(str(value))}")
    return "\n".join(lines) + "\n"


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit("PyYAML is required to load state files. Install with `python -m pip install PyYAML`.") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_yaml(data), encoding="utf-8")


def fetch_issue(repo: str, issue: int) -> dict[str, Any]:
    return gh_json([
        "issue", "view", str(issue), "--repo", repo,
        "--json", "number,title,body,state,labels,comments,assignees,url,updatedAt"
    ])


def list_candidate_issues(repo: str, label: str) -> list[dict[str, Any]]:
    return gh_json([
        "issue", "list", "--repo", repo, "--state", "open", "--label", label,
        "--limit", "50", "--json", "number,title,url,updatedAt,labels"
    ])


def approvals_from_comments(issue: dict[str, Any]) -> dict[str, bool]:
    approvals = {stage: False for stage in STAGES}
    for comment in issue.get("comments", []):
        body = (comment.get("body") or "").strip()
        match = APPROVAL_COMMENT_RE.search(body)
        if match:
            approvals[match.group(1).lower()] = True
    return approvals


def marker_exists(issue: dict[str, Any], marker: str) -> bool:
    return any(marker in (comment.get("body") or "") for comment in issue.get("comments", []))


def post_comment(repo: str, issue: int, body: str, *, apply: bool) -> None:
    if not apply:
        print(f"DRY-RUN comment issue #{issue}: {body.splitlines()[0]}")
        return
    run(["gh", "issue", "comment", str(issue), "--repo", repo, "--body", body])


def add_label(repo: str, issue: int, label: str, *, apply: bool) -> None:
    if not apply:
        print(f"DRY-RUN add label issue #{issue}: {label}")
        return
    run(["gh", "issue", "edit", str(issue), "--repo", repo, "--add-label", label])


def current_stage(state: dict[str, Any]) -> str:
    return str(state.get("stage") or "goal")


def next_stage(stage: str) -> str | None:
    try:
        idx = STAGES.index(stage)
    except ValueError:
        return "goal"
    if idx + 1 >= len(STAGES):
        return None
    return STAGES[idx + 1]


def artifact_path(state: dict[str, Any], stage: str) -> Path:
    repo = str(state["repo"])
    issue = int(state["issue"])
    return run_dir(repo, issue) / f"{stage}.md"


def write_artifact(state: dict[str, Any], issue_data: dict[str, Any], stage: str) -> Path:
    path = artifact_path(state, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    title = issue_data.get("title") or state.get("title")
    body = issue_data.get("body") or ""
    if stage == "goal":
        content = f"""# Goal\n\nIssue: {state['repo']}#{state['issue']}\nTitle: {title}\n\n## Restated goal\n\n{body.strip() or 'No issue body provided.'}\n\n## Success criteria\n\n- The goal is understood and bounded.\n- A research summary can be produced next.\n\n## Approval\n\nComment `/sp approve goal` on the issue to continue.\n"""
    elif stage == "research":
        content = f"""# Research\n\nIssue: {state['repo']}#{state['issue']}\n\n## Repository context\n\n- Inspect the target repository locally before implementation.\n- Use GitHub issue comments and labels as the audit surface.\n- Keep durable orchestration state in `.superpowers/issues/*.yaml`.\n\n## Open questions\n\n- Are there repo-specific test commands?\n- Is implementation docs-only, code, or both?\n\n## Approval\n\nComment `/sp approve research` on the issue to continue.\n"""
    elif stage == "plan":
        content = f"""# Implementation Plan\n\nIssue: {state['repo']}#{state['issue']}\n\n## Plan\n\n1. Create a branch for the issue.\n2. Write or update the smallest relevant test/verification first.\n3. Make focused changes.\n4. Run verification commands.\n5. Push a PR with evidence.\n\n## Approval\n\nComment `/sp approve plan` on the issue to allow implementation.\n"""
    elif stage == "implement":
        content = f"""# Implementation Notes\n\nIssue: {state['repo']}#{state['issue']}\n\nImplementation is approved. A local Codex session should now create a branch, implement the plan, and open a PR.\n\nComment `/sp approve implement` after implementation evidence or PR exists.\n"""
    elif stage == "test":
        content = f"""# Test Report\n\nIssue: {state['repo']}#{state['issue']}\n\nRecord exact test commands and output here.\n\nComment `/sp approve test` after test evidence is acceptable.\n"""
    elif stage == "verify":
        content = f"""# Verification\n\nIssue: {state['repo']}#{state['issue']}\n\nFresh verification is required before completion claims.\n\nComment `/sp approve verify` after verification evidence is acceptable.\n"""
    else:
        content = f"""# Release\n\nIssue: {state['repo']}#{state['issue']}\n\nRelease gate reached. Human merge/publish remains required.\n"""
    path.write_text(content, encoding="utf-8")
    return path


def ensure_state(repo: str, issue_number: int, issue_data: dict[str, Any]) -> tuple[Path, dict[str, Any], bool]:
    path = state_path(repo, issue_number)
    if path.exists():
        return path, load_yaml(path), False
    state = {
        "schema_version": "1",
        "repo": repo,
        "issue": str(issue_number),
        "issue_url": issue_data.get("url", ""),
        "title": issue_data.get("title", ""),
        "stage": "goal",
        "status": "pending",
        "branch": "",
        "pr_url": "",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "approvals": {stage: False for stage in STAGES},
        "artifacts": {},
        "history": ["created local state"],
    }
    return path, state, True


def sync_one(repo: str, issue_number: int, *, apply: bool) -> None:
    issue_data = fetch_issue(repo, issue_number)
    path, state, created = ensure_state(repo, issue_number, issue_data)
    approvals = approvals_from_comments(issue_data)
    state["approvals"] = {**{stage: False for stage in STAGES}, **state.get("approvals", {}), **approvals}
    stage = current_stage(state)

    if created:
        print(f"Created state: {path}")

    # If current stage approved, advance first; otherwise prepare current stage.
    if state["approvals"].get(stage):
        nxt = next_stage(stage)
        if nxt:
            state["history"].append(f"{now_iso()} approved {stage}; advanced to {nxt}")
            state["stage"] = nxt
            state["status"] = "pending"
            stage = nxt
        else:
            state["status"] = "done"
            state["history"].append(f"{now_iso()} release approved; done")

    artifact = write_artifact(state, issue_data, stage)
    state.setdefault("artifacts", {})[stage] = str(artifact.relative_to(ROOT)).replace("\\", "/")
    state["updated_at"] = now_iso()
    save_state(path, state)

    marker = f"<!-- local-sp:{stage} -->"
    if not marker_exists(issue_data, marker):
        comment = (
            f"{marker}\n"
            f"SP_STAGE: {stage}-ready\n\n"
            f"Local Codex Superpowers orchestrator prepared `{state['artifacts'][stage]}`.\n\n"
            f"Next: review the artifact and comment `/sp approve {stage}` to continue."
        )
        post_comment(repo, issue_number, comment, apply=apply)
    else:
        print(f"Issue #{issue_number}: marker already posted for stage {stage}")



def local_approval_comment(stage: str) -> str:
    return f"/sp approve {stage}\n\nApproved locally by Codex command."


def load_existing_or_create(repo: str, issue_number: int) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    issue_data = fetch_issue(repo, issue_number)
    path, state, _created = ensure_state(repo, issue_number, issue_data)
    if not path.exists():
        save_state(path, state)
    return path, state, issue_data


def print_status(repo: str, issue_number: int) -> None:
    path, state, issue_data = load_existing_or_create(repo, issue_number)
    approvals = approvals_from_comments(issue_data)
    merged_approvals = {**{stage: False for stage in STAGES}, **state.get("approvals", {}), **approvals}
    print(f"Issue: {repo}#{issue_number}")
    print(f"URL: {issue_data.get('url', '')}")
    print(f"State file: {path.relative_to(ROOT)}")
    print(f"Stage: {state.get('stage')}")
    print(f"Status: {state.get('status')}")
    print("Approvals:")
    for stage in STAGES:
        print(f"  {stage}: {bool(merged_approvals.get(stage))}")
    artifacts = state.get("artifacts", {}) or {}
    if artifacts:
        print("Artifacts:")
        for stage, artifact in artifacts.items():
            print(f"  {stage}: {artifact}")


def approve_stage(repo: str, issue_number: int, stage: str, *, apply: bool, audit_comment: bool = True) -> None:
    if stage not in STAGES:
        raise SystemExit(f"Unknown stage {stage!r}. Expected one of: {', '.join(STAGES)}")
    path, state, issue_data = load_existing_or_create(repo, issue_number)
    approvals = {**{s: False for s in STAGES}, **state.get("approvals", {})}
    approvals[stage] = True
    state["approvals"] = approvals
    state.setdefault("history", []).append(f"{now_iso()} locally approved {stage}")
    state["updated_at"] = now_iso()
    save_state(path, state)
    print(f"Approved locally: {stage}")
    if audit_comment:
        post_comment(repo, issue_number, local_approval_comment(stage), apply=apply)
    sync_one(repo, issue_number, apply=apply)


def run_issue(repo: str, issue_number: int, *, apply: bool) -> None:
    sync_one(repo, issue_number, apply=apply)

def main() -> int:
    parser = argparse.ArgumentParser(description="Local Codex Superpowers orchestrator")
    subparsers = parser.add_subparsers(dest="command")

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--repo", required=True, help="owner/name")
        p.add_argument("--issue", type=int, help="specific issue number")
        p.add_argument("--discover-label", default="sp:local-flow", help="label used to discover issues")
        p.add_argument("--apply", action="store_true", help="write GitHub comments/labels")
        p.add_argument("--dry-run", action="store_true", help="do not mutate GitHub (default)")

    run_parser = subparsers.add_parser("run", help="run/sync one issue or all discovered issues")
    add_common(run_parser)

    status_parser = subparsers.add_parser("status", help="show local/GitHub stage status")
    status_parser.add_argument("--repo", required=True, help="owner/name")
    status_parser.add_argument("--issue", required=True, type=int, help="issue number")

    approve_parser = subparsers.add_parser("approve", help="approve a stage locally and immediately advance")
    approve_parser.add_argument("--repo", required=True, help="owner/name")
    approve_parser.add_argument("--issue", required=True, type=int, help="issue number")
    approve_parser.add_argument("--stage", required=True, choices=STAGES)
    approve_parser.add_argument("--apply", action="store_true", help="post GitHub audit comment and stage comment")
    approve_parser.add_argument("--dry-run", action="store_true", help="update local YAML but do not mutate GitHub")
    approve_parser.add_argument("--no-audit-comment", action="store_true", help="do not post /sp approve audit comment")

    # Backward-compatible legacy flags: `script.py --repo ... --issue ...` means run.
    argv = sys.argv[1:]
    if argv and argv[0] not in {"run", "status", "approve", "-h", "--help"}:
        argv = ["run", *argv]
    args = parser.parse_args(argv)

    command = args.command or "run"
    if command == "status":
        print_status(args.repo, args.issue)
        return 0
    if command == "approve":
        approve_stage(args.repo, args.issue, args.stage, apply=args.apply, audit_comment=not args.no_audit_comment)
        return 0

    if args.issue:
        run_issue(args.repo, args.issue, apply=args.apply)
        return 0

    issues = list_candidate_issues(args.repo, args.discover_label)
    if not issues:
        print(f"No open issues with label {args.discover_label}")
        return 0
    for issue in issues:
        run_issue(args.repo, int(issue["number"]), apply=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
