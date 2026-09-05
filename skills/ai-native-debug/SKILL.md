---
name: ai-native-debug
description: Diagnose failing software behavior and route the fix to the earliest incorrect lifecycle layer. Use for bugs, regressions, flaky checks, incidents, or repeated failed fixes when the cause is not already proven.
---

# Debug before patching

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane and invariants.

## Workflow

1. State the observed symptom exactly. Capture the failing command, input, environment, and output without secrets.
2. Reproduce it or explain why reproduction is unavailable. Distinguish current evidence from reports and hypotheses.
3. Trace backward through every caller and boundary until the first incorrect state or assumption is found. Inspect sibling callers before choosing the fix point.
4. Form one falsifiable root-cause hypothesis and run the smallest discriminating check.
5. If disproved, record the result and form the next hypothesis. After three failed fix attempts, stop patching and reassess architecture, environment, and the original intent with the user.
6. Route the repair:
   - wrong desired outcome or constraint -> `ai-native-shape`
   - wrong design or approach -> `ai-native-plan`
   - implementation defect -> add a fail-first regression check and use `ai-native-build`
   - bad test or control band -> correct it only with evidence that the expected behavior is unchanged
   - release or environment defect -> `ai-native-ship`
7. Before editing, honor the selected lane. Controlled work returns through accepted intent, spec, and plan gates even when the defect is in implementation. Standard work needs an accepted plan when no current plan covers the fix.
8. Verify the original symptom and the nearest sibling flows. Then continue through review and fresh verification.

## Output

Lead with root cause, evidence, affected paths, and the correct repair layer. Do not call a hypothesis a root cause.
