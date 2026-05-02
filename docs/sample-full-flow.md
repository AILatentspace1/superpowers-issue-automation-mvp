# Sample Superpowers Full Development Flow

This sample flow demonstrates:

```text
goal -> research -> plan -> implement plan -> test -> verify -> release
```

## Labels

| Stage | Entry label | Approval label | Agent |
| --- | --- | --- | --- |
| Goal | `sp:goal` | `sp:goal-approved` | `superpowers-product-planner` |
| Research | `sp:research` | `sp:research-approved` | `superpowers-product-planner` |
| Plan | `sp:plan` | `sp:plan-approved` | `superpowers-implementation-planner` |
| Implement | `sp:implement` | `sp:implementation-ready` | `superpowers-implementer` |
| Test | `sp:test` | `sp:test-approved` | `superpowers-test-engineer` |
| Verify | `sp:verify` | `sp:verify-approved` | `superpowers-release-captain` |
| Release | `sp:release` | human merge/publish | human gate |

## Manual test recipe

1. Create an issue using the **Superpowers Sample Full Flow** template.
2. Confirm GitHub Actions posts `<!-- sp:sample:goal -->` planner comment.
3. Add label `sp:goal-approved`.
4. Confirm research comment appears.
5. Add label `sp:research-approved`.
6. Confirm implementation-planner comment appears.
7. Add label `sp:plan-approved`.
8. Confirm implementer comment appears and a PR may be created by Copilot. Add `sp:implementation-ready` when implementation evidence is acceptable.
9. On PR, confirm test-engineer comment appears.
10. Add `sp:test-approved` after test evidence is acceptable.
11. Confirm release-captain verify comment appears.
12. Add `sp:verify-approved` after verification evidence is acceptable.
13. Confirm release gate comment appears.

## Safety

- Goal, research, plan, test, and verify all require explicit approval labels.
- The workflow is idempotent: marker comments prevent duplicate prompts.
- Human merge/publish is required at release.
