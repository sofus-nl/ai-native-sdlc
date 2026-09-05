# Artifact contracts

Store Standard and Controlled work under `.sdlc/changes/<slug>/`. Use existing repository locations when they already serve the same purpose.

## `intent.md`

- Status and owner
- Problem and evidence
- Desired outcome
- Affected users and systems
- Invariants and constraints
- Out of scope
- Open questions and named decision owners
- Source-of-truth links

## `spec.md`

- Trace to intent
- Current behavior and relevant existing architecture
- Required behavior and non-goals
- Interfaces, data flow, trust boundaries, and failure behavior
- Acceptance criteria with stable IDs such as `AC-1`
- Policy conflicts, decisions, and unresolved risks
- Rollout and observability needs

## `plan.md`

- Exact files or components and why each changes
- Ordered tasks; mark dependencies and parallel waves only where files and state do not collide
- Requirement-to-proof map from each acceptance ID to a test, check, or observation
- First tracer slice for uncertain integrations
- Complexity budget: reused seam, files touched, dependencies or abstractions added, intended deletions, and any deliberate ceiling
- Risks, recovery path, and rejected alternatives
- Expected commands and healthy outcomes

## `state.md`

Keep it short and machine-readable:

```yaml
status: draft|approved|planned|building|reviewing|verified|released|monitoring|blocked
lane: standard|controlled
current_gate: intent|design|plan|build|review|verify|release|operate
next_action: one concrete action
blocker: null
updated: YYYY-MM-DD
approvals:
  - gate: intent|design|plan|review|release
    decision: accepted|rejected
    by: human identity or human-confirmed-in-session
    at: ISO-8601 timestamp
    evidence: durable link, commit, or conversation reference
```

An agent never records its own output as a human approval. Below the header, record only durable decisions, plan deviations, deferred items with owners, and evidence links.

## Evidence and review

Prefer existing test output, CI, PR, deployment, and incident systems as the record. Create `evidence.md`, `review.md`, `release.md`, or `incident.md` only when no authoritative system already holds the information.

Evidence entries name the claim, command or observation, timestamp/context, result, and limitation. Never paste secrets or large logs.
