---
name: ai-native-verify
description: Produce fresh evidence for software completion claims and acceptance criteria. Use before saying a change is fixed, complete, ready, or safe to release.
---

# Verify before claiming

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane and invariants.

## Workflow

1. List the claims that must be true: acceptance IDs, original symptom, compatibility, build health, and release readiness.
2. Map each claim to the narrowest authoritative command or observation. Tests prove behavior they exercise; lint does not prove build; build does not prove production.
3. Run every required check fresh in the current environment. Read the full result, exit status, failure count, and relevant warnings.
4. For a regression check, prove it detects the bug: use the recorded pre-fix failure, or temporarily reverse only the fix when safe and restore it immediately. Do not perform destructive proof.
5. For UI, inspect the rendered behavior at relevant viewport and interaction states. For production claims, verify the intended live endpoint or deployment, not a preview.
6. Record gaps and limitations plainly. Partial proof supports only a partial claim.
7. Re-read the diff and acceptance map. If any claim lacks evidence, return to the correct earlier skill.
8. When every accepted claim passes, stop. Do not add unrequested hardening, cleanup, tests, or documentation.
9. Update `state.md` to `verified` only when all required claims are supported. Then invoke `ai-native-ship` if release is in scope.

## Evidence format

For each claim report: `claim -> command/observation -> result -> context/limitation`.

Never rely on an earlier run, another agent's assertion, or "should."
