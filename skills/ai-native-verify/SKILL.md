---
name: ai-native-verify
description: Produce fresh evidence for software completion claims and acceptance criteria. Use before saying a change is fixed, complete, ready, or safe to release.
---

# Verify before claiming

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane and invariants.

## Workflow

1. List the claims that must be true: acceptance IDs, original symptom, compatibility, build health, and release readiness. For versioned-release claims, apply `../ai-native-sdlc/references/semver.md`; version syntax alone does not prove a compatible change or a correct bump. For model qualification claims, apply `../ai-native-sdlc/references/model-selection.md`.
2. Map each claim to the narrowest authoritative command or observation. Tests prove behavior they exercise; lint does not prove build; build does not prove production.
3. Run every required check fresh in the current environment. Read the full result, exit status, failure count, and relevant warnings.
4. For a regression check, prove it detects the bug: use the recorded pre-fix failure, or temporarily reverse only the fix when safe and restore it immediately. Do not perform destructive proof.
5. For UI, run the visual gate:
   - For a visual Reference oracle (design, screenshot, or running implementation), capture the implementation and the oracle in the same state and viewport.
   - List every discrepancy with severity and on-screen location.
   - If the captures show different states, mark the pair INVALID and recapture; do not judge it. After two failed recaptures, record the visual claim as unverified and stop for the user, including inside the build loop.
   - Any Critical or Important discrepancy within scope fails the gate.
   - Without capture tooling, ask the human to perform the comparison.
   - Scope the comparison to the change, or to the checkpoint's contribution when `ai-native-build` applies this gate per checkpoint. Build applies only this step and then continues its loop.
   - For a written oracle or Reference oracle `none`, inspect the rendered implementation against the stated requirements at the viewport and interaction states the spec names.
6. For production claims, verify the intended live endpoint or deployment, not a preview.
7. Record gaps and limitations plainly. Partial proof supports only a partial claim.
8. Re-read the diff and acceptance map. If any claim lacks evidence, return to the correct earlier skill.
9. When every accepted claim passes, stop. Do not add unrequested hardening, cleanup, tests, or documentation.
10. Update `state.md` to `verified` only when all required claims are supported. Then invoke `ai-native-ship` if release is in scope.

## Evidence format

For each claim report: `claim -> command/observation -> result -> context/limitation`.

Never rely on an earlier run, another agent's assertion, or "should."
