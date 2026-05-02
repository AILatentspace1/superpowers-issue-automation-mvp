#!/usr/bin/env python3
"""Poll GitHub issues and recommend/apply Superpowers flow next actions.

This script is intentionally small and dependency-free. It uses the GitHub CLI
(`gh`) so it can run from Codex Automations, local shells, or GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Action:
    issue_number: int
    kind: str
    detail: str
    comment: str | None = None
    add_labels: tuple[str, ...] = ()
    remove_labels: tuple[str, ...] = ()


def run_gh(args: list[str], *, input_text: str | None = None) -> str:
    completed = subprocess.run(
        ["gh", *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout


def load_issues(repo: str) -> list[dict]:
    raw = run_gh([
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        "100",
        "--json",
        "number,title,labels,comments,updatedAt,url",
    ])
    return json.loads(raw)


def label_names(issue: dict) -> set[str]:
    return {label["name"] for label in issue.get("labels", [])}


def comment_bodies(issue: dict) -> list[str]:
    return [comment.get("body") or "" for comment in issue.get("comments", [])]


def has_marker(issue: dict, marker: str) -> bool:
    return any(marker in body for body in comment_bodies(issue))


def decide(issue: dict) -> Iterable[Action]:
    labels = label_names(issue)
    n = issue["number"]

    if "sp:needs-design" in labels and not has_marker(issue, "<!-- sp:invoke:product-planner -->"):
        yield Action(
            issue_number=n,
            kind="comment",
            detail="Invoke product planner for design-only output.",
            comment=(
                "<!-- sp:invoke:product-planner -->\n"
                "@copilot use superpowers-product-planner to create a design/spec only. "
                "Do not modify files, create branches, commit, or open a PR.\n\n"
                "Required output marker:\n```text\nSP_STAGE: design-ready\n```"
            ),
        )

    if "sp:design-approved" in labels and "sp:needs-plan" not in labels:
        yield Action(
            issue_number=n,
            kind="transition",
            detail="Design approved; move issue to planning stage.",
            add_labels=("sp:needs-plan",),
            remove_labels=("sp:needs-design",),
        )

    if "sp:needs-plan" in labels and not has_marker(issue, "<!-- sp:invoke:implementation-planner -->"):
        yield Action(
            issue_number=n,
            kind="comment",
            detail="Invoke implementation planner for plan-only output.",
            comment=(
                "<!-- sp:invoke:implementation-planner -->\n"
                "@copilot use superpowers-implementation-planner to turn the approved design "
                "into an implementation plan only. Do not modify code.\n\n"
                "Required output marker:\n```text\nSP_STAGE: plan-ready\n```"
            ),
        )

    if "sp:plan-approved" in labels and "sp:needs-implementation" not in labels:
        yield Action(
            issue_number=n,
            kind="transition",
            detail="Plan approved; move issue to implementation stage.",
            add_labels=("sp:needs-implementation",),
            remove_labels=("sp:needs-plan",),
        )

    if "sp:needs-implementation" in labels and not has_marker(issue, "<!-- sp:invoke:implementer -->"):
        yield Action(
            issue_number=n,
            kind="comment",
            detail="Invoke implementer to create PR with TDD evidence.",
            comment=(
                "<!-- sp:invoke:implementer -->\n"
                "@copilot use superpowers-implementer to implement the approved plan with TDD. "
                "Create a PR when ready and include verification evidence."
            ),
        )


def apply_action(repo: str, action: Action) -> None:
    for label in action.add_labels:
        run_gh(["issue", "edit", str(action.issue_number), "--repo", repo, "--add-label", label])
    for label in action.remove_labels:
        # gh exits non-zero when the label is absent; ignore that case by using api.
        subprocess.run(["gh", "issue", "edit", str(action.issue_number), "--repo", repo, "--remove-label", label], check=False)
    if action.comment:
        run_gh(["issue", "comment", str(action.issue_number), "--repo", repo, "--body", action.comment])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="GitHub repository, e.g. owner/name")
    parser.add_argument("--apply", action="store_true", help="Apply comments and labels")
    parser.add_argument("--dry-run", action="store_true", help="Only print actions (default)")
    args = parser.parse_args()

    issues = load_issues(args.repo)
    actions: list[Action] = []
    for issue in issues:
        actions.extend(decide(issue))

    if not actions:
        print("No Superpowers issue-flow actions needed.")
        return 0

    for action in actions:
        print(f"#{action.issue_number} [{action.kind}] {action.detail}")
        if action.add_labels:
            print(f"  add_labels={','.join(action.add_labels)}")
        if action.remove_labels:
            print(f"  remove_labels={','.join(action.remove_labels)}")
        if action.comment:
            print("  comment_marker=" + action.comment.splitlines()[0])
        if args.apply:
            apply_action(args.repo, action)

    if not args.apply:
        print("Dry run only. Re-run with --apply to mutate GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
