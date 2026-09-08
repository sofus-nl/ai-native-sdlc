---
name: ai-native-plan
description: Convert accepted software intent or a specification into a codebase-grounded implementation plan with dependencies and proof. Use before changing code on multi-step or risky work.
---

# Plan from the code outward

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane and invariants.

## Workflow

1. Read the accepted source artifact and repository instructions.
2. Investigate the real flow end to end: entry points, shared functions, callers, data boundaries, tests, configuration, and release path. For a bug, reproduce or collect direct evidence before designing the fix.
3. Apply the solution ladder in `../ai-native-sdlc/references/economy.md`. Record a new dependency or abstraction only when earlier rungs cannot meet acceptance.
4. Identify the earliest layer that must change and the smallest coherent blast radius. Record alternatives only when they were plausible.
5. Write `plan.md` using `../ai-native-sdlc/references/artifact-contracts.md`.
6. Map every acceptance ID to proof. For a bug, the proof must fail for the observed defect before the fix when feasible. For UI, include an observable visual check. For integration risk, put a thin tracer slice first.
7. Divide work into reviewer-sized tasks. Mark dependencies and what blocks the next decision; assign one integration owner. Use the economy reference's delegation rule to decide which tasks, if any, need workers. Group independent, non-overlapping tasks into waves; shared files or mutable state stay sequential.
8. Name migrations, compatibility, telemetry, rollout, and rollback only when the change actually needs them. For public-contract changes or release planning, read `../ai-native-sdlc/references/semver.md`; record the release baseline, proposed version, and compatibility rationale without publishing.
9. When Git delivery is in scope, apply `../ai-native-sdlc/references/checkpoints.md`: mark coherent commit/share points, focused proof, and authorized destinations in the existing tasks. Interrogate the plan: what could break, what is most uncertain, what assumption lacks evidence, and how recovery works.
10. Update `state.md` to `planned` only after the required plan gate is accepted. Then hand off to `ai-native-build`.

## Plan quality bar

Another capable engineer should know what to change, in what order, and how to prove each result without reading the planning conversation. Do not embed large speculative code blocks; exact contracts and observable behavior matter more than guessed implementation. Omit steps and artifacts that do not change or prove the outcome.

## Stop conditions

Stop for a material unresolved choice, missing authority, unavailable secret owned by the user, or a Controlled-lane plan awaiting approval. Do not turn uncertainty into implementation detail.
