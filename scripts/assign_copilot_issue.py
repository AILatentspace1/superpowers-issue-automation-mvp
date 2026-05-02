#!/usr/bin/env python3
"""Assign an existing GitHub issue to Copilot coding agent.

Requires a user token in GH_TOKEN/GITHUB_TOKEN with permissions accepted by the
Copilot assignment API. GitHub Actions GITHUB_TOKEN is not sufficient; use a
user PAT stored as COPILOT_ASSIGN_PAT.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

FEATURE_HEADER = "issues_copilot_assignment_api_support,coding_agent_model_selection"


def gh_graphql(query: str, variables: dict[str, str]) -> dict:
    cmd = ["gh", "api", "graphql", "-H", f"GraphQL-Features: {FEATURE_HEADER}", "-f", f"query={query}"]
    for key, value in variables.items():
        cmd.extend(["-f", f"{key}={value}"])
    completed = subprocess.run(cmd, text=True, capture_output=True, check=True)
    return json.loads(completed.stdout)


def split_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ValueError("--repo must be owner/name")
    owner, name = repo.split("/", 1)
    return owner, name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--issue", required=True, type=int)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--custom-agent", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--instructions", required=True)
    args = parser.parse_args()

    if not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        raise SystemExit("GH_TOKEN or GITHUB_TOKEN must be set")

    owner, name = split_repo(args.repo)
    query = """
query($owner:String!, $name:String!, $issue:Int!) {
  repository(owner: $owner, name: $name) {
    id
    issue(number: $issue) { id title }
    suggestedActors(capabilities: [CAN_BE_ASSIGNED], first: 100) {
      nodes {
        login
        __typename
        ... on Bot { id }
        ... on User { id }
      }
    }
  }
}
"""
    data = gh_graphql(query, {"owner": owner, "name": name, "issue": str(args.issue)})["data"]["repository"]
    repo_id = data["id"]
    issue_id = data["issue"]["id"]
    actors = data["suggestedActors"]["nodes"]
    copilot = next((actor for actor in actors if actor.get("login") == "copilot-swe-agent"), None)
    if not copilot:
        available = ", ".join(actor.get("login", "<unknown>") for actor in actors)
        raise SystemExit(f"copilot-swe-agent is not assignable. Available: {available}")

    mutation = """
mutation($issueId:ID!, $botId:ID!, $repoId:ID!, $baseRef:String!, $instructions:String!, $customAgent:String!, $model:String!) {
  updateIssue(input: {
    id: $issueId,
    assigneeIds: [$botId],
    agentAssignment: {
      targetRepositoryId: $repoId,
      baseRef: $baseRef,
      customInstructions: $instructions,
      customAgent: $customAgent,
      model: $model
    }
  }) {
    issue {
      number
      title
      assignees(first: 10) { nodes { login } }
    }
  }
}
"""
    result = gh_graphql(
        mutation,
        {
            "issueId": issue_id,
            "botId": copilot["id"],
            "repoId": repo_id,
            "baseRef": args.base_ref,
            "instructions": args.instructions,
            "customAgent": args.custom_agent,
            "model": args.model,
        },
    )
    print(json.dumps(result["data"]["updateIssue"]["issue"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
