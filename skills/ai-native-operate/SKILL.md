---
name: ai-native-operate
description: Triage production signals, incidents, and recurring defects into bounded diagnosis, repair, and lifecycle learning. Use for maintenance after release or for monitoring-triggered work.
---

# Operate the loop

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane, invariants, and operational authority.

## Workflow

1. Accept a deterministic monitor breach or a direct incident report. Verify the report against current telemetry when access exists; do not dismiss it merely because no control band fired. The agent does not invent signals or silently move thresholds.
2. Capture timestamp, environment, deployed revision, affected users/systems, control band or report source, raw evidence location, and current mitigation.
3. Assess active impact before deep diagnosis. If an existing runbook action is specifically authorized, contain harm first; examples are disabling a feature, failing over, rate-limiting, or rolling back. Otherwise surface the exact approval needed.
4. Classify the remaining authorized action:
   - observe and report;
   - read-only diagnosis;
   - prepare a bounded patch or PR;
   - execute a specifically pre-authorized rollback.
5. Use `ai-native-debug` for diagnosis. Keep production writes behind existing tools, permissions, and human gates.
6. Route a small proven defect through plan/build/review/verify. Route a wider product or architectural issue to a new `intent.md` and `ai-native-shape`.
7. After resolution, preserve the incident record in the authoritative system. Add the incident as a permanent regression or eval case when feasible.
8. Update repository guidance only for a repeated, verified lesson. Remove stale guidance rather than accumulating folklore.
9. Record dismissals with reasons and tune noisy bands through reviewed deterministic changes.

## Boundaries

- Monitoring, deployment, and rollback permissions are separate. Never treat access to one as access to the others.
- Never expose secrets or personal data in prompts or lifecycle artifacts.
- Do not claim recovery until fresh production-relevant evidence supports it.
