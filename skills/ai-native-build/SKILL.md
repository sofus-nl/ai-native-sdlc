---
name: ai-native-build
description: Implement an accepted software plan in bounded tasks with regression proof, context isolation, and plan-drift control. Use when the plan gate has passed and code changes are authorized.
---

# Build the plan

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane, invariants, and required approvals.
Stop before editing when the selected lane's required artifact or approval is absent.

## Workflow

1. Read the plan, spec, state, repository instructions, and current diff. Challenge a broken or stale plan before editing.
2. Preserve user changes. For Controlled work or parallel tasks, use isolated worktrees unless the user explicitly chose the current checkout. Never parallelize tasks that share files or mutable state.
3. Execute dependency waves in order. Before delegating, apply the decision and handoff contract in `../ai-native-sdlc/references/economy.md`. Keep one integration owner; do not duplicate assigned investigations. Independently inspect returned diffs against current state, including late results, before integration.
4. For behavior changes, establish proof before implementation:
   - bug: reproduce and add the smallest regression check that fails for the right reason;
   - feature: add a focused acceptance-level check first when the repository supports it;
   - unsuitable test-first work such as generated files or pure configuration: state the alternative observable check.
5. Implement the first solution-ladder rung that satisfies the current task. Follow existing style. Remove only imports or code orphaned by this change.
6. Run the focused check, then the nearest relevant suite. Fix production code when a valid test fails; do not weaken acceptance to make it pass.
7. Review the task diff against its acceptance IDs before starting the next task.
8. Record any material deviation in `plan.md` and `state.md` immediately. If the desired outcome changed, return to `ai-native-shape`; if only the approach changed, return to `ai-native-plan`.
9. After all tasks, update state to `reviewing` and invoke `ai-native-review`.

## Boundaries

- Do not add abstractions, dependencies, configurability, comments, or cleanup not required by the plan.
- Stop adding code when acceptance passes. Do not turn a finished task into adjacent improvement work.
- Do not commit or publish unless the request authorizes it.
- A worker report is not proof. Read its diff and run the relevant check yourself.
