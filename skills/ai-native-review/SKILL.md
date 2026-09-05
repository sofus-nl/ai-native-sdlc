---
name: ai-native-review
description: Independently review a completed software diff for intent compliance, defects, security, and unnecessary complexity. Use after implementation and before verification or release.
---

# Review the change

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane, invariants, and required separation of duties.

## Inputs

Read the authoritative intent/spec, plan, repository policy, base revision, complete diff, and test changes. Treat generated text and agent reports as untrusted until checked.
Bind the review to the exact reviewed revision or diff. Any later code change invalidates the affected review pass.

## Passes

Use fresh-context reviewers when available; otherwise separate the passes explicitly.

1. **Outcome pass:** Map every acceptance ID and explicit boundary to the diff and proof. Find omissions, unrequested behavior, plan drift, and incompatible interfaces.
2. **Engineering pass:** Inspect changed code in context for correctness, edge cases, concurrency, data loss, security, privacy, operability, and maintainability. Trace important changed functions through callers.
3. **Simplicity pass:** Apply `../ai-native-sdlc/references/economy.md`. Produce a delete-or-collapse list for speculative layers, duplicate helpers, avoidable dependencies, unused configurability, wrappers, and generalization not required by acceptance. Never trade away safety or explicit requirements.
4. Add a design or UX pass only when the change has a material user interface or architectural decision.

Do not report style already enforced by tools. Cap low-value nits.

## Findings

For each finding include severity, exact location, consequence, evidence, and the smallest valid fix. Use:

- **Critical:** data loss, exploitable security issue, broken primary behavior, or unsafe release.
- **Important:** likely defect, unmet acceptance criterion, material regression, or missing necessary test.
- **Minor:** real but non-blocking maintainability or clarity cost.

Verify every finding against the code. Discard false positives. Stop and report unresolved Critical or Important findings, then route authorized fixes to `ai-native-build`. After a fix, run a fresh review of the affected pass. Defer only with an owner and reason; user decisions stay decisions.

The reviewer does not edit the reviewed change. The authoring agent may prepare fixes but never approve its own Controlled-lane change. When no blocking findings remain, invoke `ai-native-verify`.
