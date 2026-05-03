# Goal

Issue: AILatentspace1/superpowers-issue-automation-mvp#18
Title: feat: sp converse — LLM conversation per stage with one-shot artifact extraction (C1)

## Restated goal

Add an interactive `sp converse` workflow so a user can discuss a specific GitHub issue + Superpowers stage with an LLM, then produce the stage artifact from the conversation. The current implementation now establishes the required storage model first: Superpowers YAML state and durable stage artifacts belong in the issue's target repo, not in the orchestrator repo.

## Selected approach

Use C1 - one-shot summarization for the conversation MVP.

The user has a free-form multi-turn conversation and types `/done`. The local CLI then sends the full conversation history to the LLM with a summarize-to-artifact prompt and writes the resulting Markdown artifact.

~~~text
[free conversation, N turns] -> [/done handled by CLI] -> [summarize prompt + history] -> <stage>.md
~~~

Latest implementation decision: project aliases resolve to a target GitHub repo, and all durable Superpowers files for that issue are written, committed, pushed, and linked from that target repo.

## Success criteria

- `python scripts/sp.py converse 18 --stage goal` starts an interactive conversation scoped to issue #18 and the goal stage.
- `/done` is handled by local CLI code, not by asking the LLM to decide when the conversation is finished.
- YAML state is stored in the target repo at `.superpowers/issues/issue-<n>.yaml`.
- Stage artifacts are stored in the target repo at `.superpowers/runs/issue-<n>/<stage>.md`.
- Ready comments include a GitHub blob URL for the committed target-repo artifact.
- `--apply` commits and pushes only the current issue state/artifact files in the target repo.
- `--dry-run` does not clone, write, commit, push, or update GitHub; it only prints the target paths/actions.
- Missing target repo checkout in `--apply` mode is handled by cloning `git@github.com:OWNER/REPO.git` into the workspace.
- Missing API key/model/provider errors for the future conversation command are clear and actionable.
- README / command docs include `SP_LLM_*` configuration and usage examples when `sp converse` is implemented.

## Constraints

- Project alias config remains in the orchestrator repo under `.superpowers/projects/*.yaml`.
- Runtime pointer `.superpowers/current_project` remains local-only.
- Durable issue state and artifacts must be in the target repo, not the orchestrator repo.
- Default local target checkout path is `E:/workspace/<repo-name>`.
- Existing target checkout must have an `origin` remote matching the project repo; otherwise the orchestrator must refuse to write.
- `sp converse` should support planning-oriented stages first: `goal`, `research`, and `plan`.
- Conversation output should use the deterministic artifact template for the current stage.

## Non-goals

- Do not implement C2 schema-driven interview flow in this issue.
- Do not implement C3 rolling summary in this issue.
- Do not support automatic stage approval or stage advancement from `/done`.
- Do not auto-post GitHub `/sp approve <stage>` comments from the conversation command.
- Do not require all seven stages to support conversation in MVP.
- Do not commit raw conversation logs by default.
- Do not use the orchestrator repo as the durable storage location for another repo's issue state/artifacts.

## Open questions

- Should conversation be allowed for `implement`, `test`, `verify`, or `release` later, or remain limited to planning stages?
- Should future versions support a compact/resumed summary for very long conversations?
- Should provider support remain minimal OpenAI-compatible HTTP, or introduce a provider abstraction?
- Should raw conversation logs be generated in MVP, and should they remain local-only under the target repo's `.superpowers/runs/issue-<n>/<stage>.conversation.jsonl` instead of being committed?

## Source relationship

- GitHub issue #18 is the product source of truth and detailed history.
- This `goal.md` is the approvable product-planner snapshot for the current stage.
- If the issue and this artifact conflict, refresh this artifact from the latest issue before approval.

## Approval

Comment `/sp approve goal` on the issue to continue.
