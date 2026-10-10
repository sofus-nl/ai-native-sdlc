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
3. Resume at the checkpoint named in `next_action`; if `status: blocked`, obtain and record the pending approval first. Route fixes after the full review to the affected checkpoint only. Set `status: building`. For each remaining checkpoint in `plan.md`, in order:
   1. Read the human feedback recorded in `state.md`.
   2. Execute the checkpoint's dependency waves. Before delegating, apply the decision and handoff contract in `../ai-native-sdlc/references/economy.md`. Keep one integration owner; do not duplicate assigned investigations. Independently inspect returned diffs against current state, including late results, before integration.
   3. For behavior changes, establish proof before implementation:
      - bug: reproduce and add the smallest regression check that fails for the right reason;
      - feature: add a focused acceptance-level check first when the repository supports it;
      - unsuitable test-first work such as generated files or pure configuration: state the alternative observable check;
      - Controlled: a separate test-author worker writes the checks from the spec and Reference oracle when the host supports it. The implementer does not edit or dismiss those checks; disputes go to the reviewers or the human.
   4. Implement the first solution-ladder rung that satisfies the checkpoint completely, with no placeholder or deferred part. Follow existing style. Remove only imports or code orphaned by this change.
   5. Run gates cheapest first: the focused check, then the nearest relevant suite; the visual gate in `../ai-native-verify/SKILL.md` only when the checkpoint changes UI; then self-review the checkpoint diff against its acceptance IDs and hunt for defects, placeholders, and unhandled cases. Controlled also invokes the `ai-native-review` skill in checkpoint mode: two context-isolated reviewers, and both must approve. Dispatching a reviewer agent without that skill does not satisfy this gate. Fix production code when a valid test fails; do not weaken acceptance to make it pass.
   6. A fix re-runs every gate it affects; a visible change re-runs the visual gate. A round is one pass through all of the checkpoint's gates. After three rounds without convergence, stop and reassess with the user.
   7. When Git checkpoints are authorized, apply `../ai-native-sdlc/references/checkpoints.md`: commit the checked checkpoint and push for CI, feedback, or handoff within the permitted scope. Do not defer every commit until the build finishes or confuse a branch push with merge readiness.
   8. Controlled: stop for human approval after checkpoint 1, even when the request already authorizes implementation. Before stopping, set `status: blocked`, `blocker: awaiting checkpoint approval n/total`, and `next_action: obtain checkpoint approval n/total`. Record the resulting `checkpoint` approval with its scope, then set `status: building` and `blocker: null`. Before starting any later checkpoint, confirm a recorded approval covers it; otherwise stop again. The stop after checkpoint 1 is the only mandatory approval stop: do not ask for approval to start a later checkpoint that a recorded `checkpoint` approval already covers, nor to start the full review and verification after the last checkpoint. Record human feedback in `state.md` and set `next_action` to the next checkpoint.
4. Record any material deviation in `plan.md` and `state.md` immediately. If the desired outcome changed, return to `ai-native-shape`; if only the approach changed, return to `ai-native-plan`.
5. After all checkpoints, update state to `reviewing` and invoke the `ai-native-review` skill on the full diff; it hands off to `ai-native-verify`. Do not report the change complete before verification finishes.

## Boundaries

- Do not add abstractions, dependencies, configurability, comments, or cleanup not required by the plan.
- Stop adding code when acceptance passes. Do not turn a finished task into adjacent improvement work.
- Do not commit or publish unless the request authorizes it.
- A worker report is not proof. Read its diff and run the relevant check yourself.
