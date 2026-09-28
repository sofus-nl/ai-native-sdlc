---
name: ai-native-plan
description: Convert accepted software intent or a specification into a codebase-grounded implementation plan with dependencies and proof. Use before changing code on multi-step or risky work.
---

# Plan from the code outward

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane and invariants.
Stop when the selected lane's required source artifact or approval is absent, except that a plan-only request may draft `plan.md` on draft intent and spec; mark nothing accepted and record no approval. Standard and Controlled plans need a `spec.md` with acceptance IDs and a Reference oracle; when it is missing, invoke `ai-native-shape` first.

## Workflow

1. Read the accepted source artifact and repository instructions.
2. Investigate the real flow end to end: entry points, shared functions, callers, data boundaries, tests, configuration, and release path. For a bug, reproduce or collect direct evidence before designing the fix.
3. Apply the solution ladder in `../ai-native-sdlc/references/economy.md`. Record a new dependency or abstraction only when earlier rungs cannot meet acceptance.
4. Identify the earliest layer that must change and the smallest coherent blast radius. Record alternatives only when they were plausible.
5. Write `plan.md` using `../ai-native-sdlc/references/artifact-contracts.md`.
6. Map every acceptance ID to proof. For a bug, the proof must fail for the observed defect before the fix when feasible. For UI, include an observable visual check. For integration risk, put a thin tracer slice first.
7. Divide work into reviewer-sized tasks and group them into ordered checkpoints of increasing complexity. Checkpoint 1 is the thinnest end-to-end slice, the tracer slice when integration risk exists. Summarize each checkpoint in one line a human can approve quickly. Mark dependencies and what blocks the next decision; assign one integration owner. Use the economy reference's delegation rule to decide which tasks, if any, need workers. Group independent, non-overlapping tasks into waves only inside a checkpoint; shared files or mutable state stay sequential.
8. Name migrations, compatibility, telemetry, rollout, and rollback only when the change actually needs them. For public-contract changes or release planning, read `../ai-native-sdlc/references/semver.md`; record the release baseline, proposed version, and compatibility rationale without publishing.
9. When Git delivery is in scope, apply `../ai-native-sdlc/references/checkpoints.md`: mark commit/share points, focused proof, and authorized destinations on the existing checkpoints. Interrogate the plan: what could break, what is most uncertain, what assumption lacks evidence, and how recovery works.
10. Stop for human acceptance of the plan and its checkpoint list. Plan acceptance does not replace the Controlled approval after checkpoint 1. While waiting, keep `status: draft` with `next_action: obtain plan approval`. After acceptance, record the `plan` approval, set `status: planned`, then hand off to `ai-native-build`.

## Plan quality bar

Another capable engineer should know what to change, in what order, and how to prove each result without reading the planning conversation. Do not embed large speculative code blocks; exact contracts and observable behavior matter more than guessed implementation. Omit steps and artifacts that do not change or prove the outcome.

## Stop conditions

Stop for a material unresolved choice, missing authority, unavailable secret owned by the user, or a plan awaiting approval. Do not turn uncertainty into implementation detail.
