# Goal

Issue: AILatentspace1/superpowers-issue-automation-mvp#18
Title: feat: sp converse — LLM conversation per stage with one-shot artifact extraction (C1)

## Restated goal

Currently write_artifact generates static template content with no LLM involvement. The goal is to let a user have a multi-turn LLM conversation scoped to a specific GitHub issue plus Superpowers stage, then extract the conversation conclusions into that stage artifact.

## Selected approach

Use C1 - one-shot summarization for the MVP.

After free-form conversation, the user types /done. The local CLI then sends the conversation history to the LLM with a summarize-to-artifact prompt and writes the resulting Markdown artifact.

~~~text
[free conversation, N turns] -> [/done handled by CLI] -> [summarize prompt + history] -> <stage>.md
~~~

- Keeps the first version small and compatible with the existing stage artifact model.
- Supports natural multi-turn planning without requiring per-stage schemas upfront.
- Avoids the extra state complexity of rolling summaries.

## Success criteria

- python scripts/sp.py converse 18 --stage goal starts an interactive conversation scoped to issue #18 and goal stage.
- /done is handled by local CLI code, not by asking the LLM to decide when the conversation is finished.
- Conversation turns are persisted to .superpowers/runs/<repo>/issue-18/goal.conversation.jsonl.
- Final summary overwrites or writes .superpowers/runs/<repo>/issue-18/goal.md using the goal artifact structure above.
- The command does not approve, advance, comment on GitHub, create branches, or open PRs.
- Missing API key/model/provider errors are clear and actionable.
- README / command docs include SP_LLM_* configuration and usage examples.

## Constraints

- Add command: python scripts/sp.py converse <issue> [--stage <stage>].
- Default --stage to the current active stage from local Superpowers state.
- Support conversation for planning-oriented stages first: goal, research, and plan.
- Load issue data, current stage, and existing artifact as context.
- Save raw turns to <stage>.conversation.jsonl under .superpowers/runs/....
- On /done, produce the stage artifact Markdown and write <stage>.md.
- Configure LLM via env vars: SP_LLM_PROVIDER, SP_LLM_API_KEY or OPENAI_API_KEY, and SP_LLM_MODEL.
- Document env vars and command usage in README / command docs.

## Non-goals

- Do not implement C2 schema-driven interview flow in this issue.
- Do not implement C3 rolling summary in this issue.
- Do not support automatic stage approval or stage advancement from /done.
- Do not auto-post GitHub /sp approve <stage> comments from the conversation command.
- Do not require all seven stages to support conversation in MVP.
- Do not implement proxy support unless existing HTTP client configuration already supports it naturally.

## Open questions

- Should conversation be allowed for implement, test, verify, or release later, or remain limited to planning stages?
- Should future versions support a compact/resumed summary for very long conversations?
- Should provider support remain minimal OpenAI-compatible HTTP, or introduce a provider abstraction?

## Source relationship

- GitHub issue #18 is the product source of truth and detailed history.
- This `goal.md` is the approvable product-planner snapshot for the current stage.
- If the issue and this artifact conflict, refresh this artifact from the issue before approval.

## Approval

Comment `/sp approve goal` on the issue to continue.
