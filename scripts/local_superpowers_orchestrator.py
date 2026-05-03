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
DEFAULT_WORKSPACE_ROOT = ROOT.parent

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


def repo_dir_name(repo: str) -> str:
    if "/" not in repo:
        raise SystemExit("--repo must be owner/name")
    return repo.split("/", 1)[1]


def normalize_repo_url(value: str) -> str:
    value = value.strip()
    if value.startswith("git@github.com:"):
        value = value.removeprefix("git@github.com:")
    elif value.startswith("https://github.com/"):
        value = value.removeprefix("https://github.com/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.strip("/")


def validate_target_repo_checkout(target_root: Path, repo: str) -> None:
    if not (target_root / ".git").exists():
        raise RuntimeError(f"Target path exists but is not a git checkout: {target_root}")
    remote = run(["git", "-C", str(target_root), "remote", "get-url", "origin"]).stdout.strip()
    if normalize_repo_url(remote).lower() != repo.lower():
        raise RuntimeError(
            f"Target checkout remote mismatch for {target_root}: "
            f"origin is {remote!r}, expected GitHub repo {repo!r}"
        )


def resolve_target_repo(
    repo: str,
    *,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    apply: bool,
) -> Path:
    """Return the local checkout for the target repo, cloning only in apply mode."""
    target_root = workspace_root / repo_dir_name(repo)
    if target_root.exists():
        validate_target_repo_checkout(target_root, repo)
        return target_root
    if not apply:
        print(f"DRY-RUN would clone target repo {repo} into {target_root}")
        return target_root
    target_root.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", f"git@github.com:{repo}.git", str(target_root)])
    return target_root


def state_path(target_root: Path, issue: int) -> Path:
    return target_root / ".superpowers" / "issues" / f"issue-{issue}.yaml"


def legacy_state_path(repo: str, issue: int) -> Path:
    return ROOT / ".superpowers" / "issues" / f"{slug_repo(repo)}__{issue}.yaml"


def run_dir(target_root: Path, issue: int) -> Path:
    return target_root / ".superpowers" / "runs" / f"issue-{issue}"


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


def marker_comment(issue: dict[str, Any], marker: str) -> dict[str, Any] | None:
    for comment in issue.get("comments", []):
        if marker in (comment.get("body") or ""):
            return comment
    return None


def post_comment(repo: str, issue: int, body: str, *, apply: bool) -> None:
    if not apply:
        print(f"DRY-RUN comment issue #{issue}: {body.splitlines()[0]}")
        return
    run(["gh", "issue", "comment", str(issue), "--repo", repo, "--body", body])


def update_comment(repo: str, comment_id: int, body: str, *, apply: bool) -> None:
    if not apply:
        print(f"DRY-RUN update comment {comment_id}: {body.splitlines()[0]}")
        return
    run(["gh", "api", "-X", "PATCH", f"repos/{repo}/issues/comments/{comment_id}", "-f", f"body={body}"])


def find_rest_comment_id(repo: str, issue: int, marker: str) -> int | None:
    comments = gh_json(["api", f"repos/{repo}/issues/{issue}/comments"])
    for comment in comments:
        if marker in (comment.get("body") or ""):
            return int(comment["id"])
    return None


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


def artifact_path(target_root: Path, state: dict[str, Any], stage: str) -> Path:
    issue = int(state["issue"])
    return run_dir(target_root, issue) / f"{stage}.md"


def normalize_heading(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def markdown_sections(markdown: str) -> dict[str, str]:
    """Return markdown sections keyed by normalized heading.

    The section body ends at the next heading with the same or higher level.
    This lets goal artifacts summarize specific issue sections instead of
    copying the full issue body.
    """
    headings: list[tuple[int, str, int, int]] = []
    for match in re.finditer(r"^(#{2,6})\s+(.+?)\s*$", markdown, flags=re.M):
        headings.append((len(match.group(1)), normalize_heading(match.group(2)), match.start(), match.end()))

    sections: dict[str, str] = {}
    for idx, (level, key, _start, body_start) in enumerate(headings):
        body_end = len(markdown)
        for next_level, _next_key, next_start, _next_body_start in headings[idx + 1:]:
            if next_level <= level:
                body_end = next_start
                break
        sections[key] = markdown[body_start:body_end].strip()
    return sections


def first_section(sections: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = sections.get(normalize_heading(name), "").strip()
        if value:
            return value
    return ""


def first_paragraph(markdown: str) -> str:
    cleaned = re.sub(r"^#{1,6}\s+.*$", "", markdown, flags=re.M).strip()
    for part in re.split(r"\n\s*\n", cleaned):
        part = part.strip()
        if part:
            return part
    return ""


def section_intro(markdown: str) -> str:
    """Return text before nested headings in a section."""
    return re.split(r"^#{3,6}\s+.+?\s*$", markdown, maxsplit=1, flags=re.M)[0].strip()


def placeholder(text: str) -> str:
    return f"- TODO: {text}"


def render_goal_artifact(state: dict[str, Any], issue_data: dict[str, Any]) -> str:
    title = issue_data.get("title") or state.get("title")
    body = issue_data.get("body") or ""
    sections = markdown_sections(body)

    restated_goal = first_section(sections, ["Problem", "Goal", "Idea"]) or first_paragraph(body)
    selected_source = first_section(sections, ["Product-planner decision", "Decision", "Selected approach"])
    selected = "\n\n".join(
        part for part in [
            section_intro(selected_source) or selected_source,
            first_section(sections, ["Why C1", "Why this approach"]),
        ] if part
    )
    success = first_section(sections, ["Success criteria", "Acceptance criteria"])
    constraints = first_section(sections, ["In scope", "Constraints"])
    non_goals = first_section(sections, ["Out of scope / non-goals", "Non-goals", "Out of scope"])
    open_questions = first_section(sections, ["Open questions for research / plan", "Open questions"])

    return f"""# Goal

Issue: {state['repo']}#{state['issue']}
Title: {title}

## Restated goal

{restated_goal or placeholder('Restate the user goal from the source issue before approving.')}

## Selected approach

{selected or placeholder('Record the product-planner selected direction and rationale before approving.')}

## Success criteria

{success or placeholder('List concrete, issue-specific acceptance criteria before approving.')}

## Constraints

{constraints or placeholder('List constraints that bound the research and implementation plan.')}

## Non-goals

{non_goals or placeholder('List explicit out-of-scope items to prevent implementation drift.')}

## Open questions

{open_questions or placeholder('List decisions that must be resolved in research or planning.')}

## Source relationship

- GitHub issue #{state['issue']} is the product source of truth and detailed history.
- This `goal.md` is the approvable product-planner snapshot for the current stage.
- If the issue and this artifact conflict, refresh this artifact from the issue before approval.

## Approval

Comment `/sp approve goal` on the issue to continue.
"""


def current_git_branch(target_root: Path) -> str:
    branch = run(["git", "-C", str(target_root), "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if not branch or branch == "HEAD":
        raise RuntimeError("Cannot publish artifact URL from detached HEAD.")
    return branch


def github_blob_url(repo: str, branch: str, target_root: Path, artifact: Path) -> str:
    relative_path = str(artifact.relative_to(target_root)).replace("\\", "/")
    return f"https://github.com/{repo}/blob/{branch}/{relative_path}"


def publish_files(repo: str, issue: int, stage: str, target_root: Path, files: list[Path], *, apply: bool) -> str | None:
    """Commit and push target-repo state/artifact files, returning artifact URL.

    Only the provided files are staged and committed. Existing staged changes are
    rejected so the orchestrator cannot accidentally commit unrelated work.
    """
    artifact = next((f for f in files if f.suffix == ".md"), files[-1])
    rels = [str(f.relative_to(target_root)).replace("\\", "/") for f in files]
    branch = current_git_branch(target_root)
    url = github_blob_url(repo, branch, target_root, artifact)

    if not apply:
        print(f"DRY-RUN publish target repo files: {', '.join(rels)} -> {url}")
        return url

    staged = run(["git", "-C", str(target_root), "diff", "--cached", "--name-only"]).stdout.strip()
    if staged:
        raise RuntimeError(
            "Refusing to publish Superpowers files while unrelated staged changes exist:\n"
            + staged
        )

    run(["git", "-C", str(target_root), "add", "-f", "--", *rels])
    diff = run(["git", "-C", str(target_root), "diff", "--cached", "--name-only", "--", *rels]).stdout.strip()
    if not diff:
        print(f"Superpowers files already committed: {', '.join(rels)}")
    else:
        run([
            "git", "-C", str(target_root), "commit",
            "-m", f"Update {stage} Superpowers files for issue #{issue}",
            "--", *rels,
        ])

    run(["git", "-C", str(target_root), "push", "-u", "origin", branch])
    return url


def write_artifact(target_root: Path, state: dict[str, Any], issue_data: dict[str, Any], stage: str) -> Path:
    path = artifact_path(target_root, state, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    title = issue_data.get("title") or state.get("title")
    body = issue_data.get("body") or ""
    if stage == "goal":
        content = render_goal_artifact(state, issue_data)
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


def ready_comment_body(state: dict[str, Any], stage: str, artifact_url: str | None) -> str:
    artifact_path = state["artifacts"][stage]
    lines = [
        f"<!-- local-sp:{stage} -->",
        f"SP_STAGE: {stage}-ready",
        "",
        f"Local Codex Superpowers orchestrator prepared `{artifact_path}`.",
    ]
    if artifact_url:
        lines.extend(["", f"Artifact: {artifact_url}"])
    lines.extend(["", f"Next: review the artifact and comment `/sp approve {stage}` to continue."])
    return "\n".join(lines)


def ensure_state(target_root: Path, repo: str, issue_number: int, issue_data: dict[str, Any]) -> tuple[Path, dict[str, Any], bool]:
    path = state_path(target_root, issue_number)
    if path.exists():
        return path, load_yaml(path), False
    legacy_path = legacy_state_path(repo, issue_number)
    if legacy_path.exists():
        return path, load_yaml(legacy_path), True
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
    target_root = resolve_target_repo(repo, apply=apply)
    if not target_root.exists():
        print(f"DRY-RUN target repo checkout missing; state/artifact would live under: {target_root}")
        return
    path, state, created = ensure_state(target_root, repo, issue_number, issue_data)
    approvals = approvals_from_comments(issue_data)
    state["approvals"] = {**{stage: False for stage in STAGES}, **state.get("approvals", {}), **approvals}
    stage = current_stage(state)

    if created:
        if apply:
            print(f"Created state: {path}")
        else:
            print(f"DRY-RUN would create/update state: {path}")

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

    artifact = artifact_path(target_root, state, stage)
    if not isinstance(state.get("artifacts"), dict):
        state["artifacts"] = {}
    artifact_rel = str(artifact.relative_to(target_root)).replace("\\", "/")
    state["artifacts"][stage] = artifact_rel
    if apply:
        artifact = write_artifact(target_root, state, issue_data, stage)
        state["updated_at"] = now_iso()
        save_state(path, state)
    else:
        print(f"DRY-RUN would write artifact: {artifact}")

    marker = f"<!-- local-sp:{stage} -->"
    artifact_url = publish_files(repo, issue_number, stage, target_root, [path, artifact], apply=apply)
    comment = ready_comment_body(state, stage, artifact_url)
    existing_comment = marker_comment(issue_data, marker)
    if not existing_comment:
        post_comment(repo, issue_number, comment, apply=apply)
    elif artifact_url and artifact_url not in (existing_comment.get("body") or ""):
        comment_id = find_rest_comment_id(repo, issue_number, marker)
        if comment_id is None:
            post_comment(repo, issue_number, comment, apply=apply)
        else:
            update_comment(repo, comment_id, comment, apply=apply)
    else:
        print(f"Issue #{issue_number}: marker already posted for stage {stage}")



def local_approval_comment(stage: str) -> str:
    return f"/sp approve {stage}\n\nApproved locally by Codex command."


def load_existing_or_create(repo: str, issue_number: int, *, apply: bool = False) -> tuple[Path, dict[str, Any], dict[str, Any], Path]:
    issue_data = fetch_issue(repo, issue_number)
    target_root = resolve_target_repo(repo, apply=apply)
    if not target_root.exists():
        raise SystemExit(f"Target repo checkout not found: {target_root}")
    path, state, _created = ensure_state(target_root, repo, issue_number, issue_data)
    if not path.exists():
        save_state(path, state)
    return path, state, issue_data, target_root


def print_status(repo: str, issue_number: int) -> None:
    path, state, issue_data, target_root = load_existing_or_create(repo, issue_number, apply=False)
    approvals = approvals_from_comments(issue_data)
    merged_approvals = {**{stage: False for stage in STAGES}, **state.get("approvals", {}), **approvals}
    print(f"Issue: {repo}#{issue_number}")
    print(f"URL: {issue_data.get('url', '')}")
    print(f"Target repo: {target_root}")
    print(f"State file: {path.relative_to(target_root)}")
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
    path, state, issue_data, _target_root = load_existing_or_create(repo, issue_number, apply=apply)
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
