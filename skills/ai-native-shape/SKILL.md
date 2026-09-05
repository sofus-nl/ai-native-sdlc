---
name: ai-native-shape
description: Turn an unclear software idea, request, or incident into accepted intent and an implementation-ready specification. Use before planning when desired behavior, constraints, or success criteria are unsettled.
---

# Shape the change

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane and invariants.

## Workflow

1. Read repository instructions and inspect the current product and code paths before proposing a design.
2. Capture the user's words as the problem, desired outcome, constraints, invariants, and out-of-scope boundary. Separate facts, assumptions, and open questions.
3. Ask only questions whose answers materially change the result. Prefer one compact batch when the questions are independent.
4. For material product choices, offer two or three genuinely different approaches with tradeoffs and an honest recommendation. For an obvious bounded change, state the single approach.
5. Challenge unsupported premises. Preserve disagreement and the deciding evidence.
6. Choose the lane using `../ai-native-sdlc/references/operating-model.md`.
7. For Standard or Controlled work, write `intent.md` using `../ai-native-sdlc/references/artifact-contracts.md`. Do not mark it accepted until the authorized human accepts it.
8. After intent acceptance, produce `spec.md`. Trace every requirement to the intent, assign acceptance IDs, describe failure behavior and trust boundaries, and flag policy conflicts.
9. Self-review for placeholders, contradictions, unowned decisions, scope creep, and acceptance criteria that cannot be tested or observed.
10. Stop at the design gate when human judgment is required. Otherwise hand the accepted spec to `ai-native-plan`.

## Boundaries

- Do not write implementation code in this skill.
- Do not invent customer evidence, policy, deadlines, or technical constraints.
- A design mock, ticket, or chat transcript may be authoritative; link it and name the source of truth.
- Keep discovery proportional. A Fast-lane edit needs a few clear sentences, not files.

## Output

Report the chosen lane, accepted decisions, unresolved questions with owners, and the next gate.
