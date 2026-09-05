---
name: ai-native-ship
description: Move a verified software change through commit, PR, CI, deployment, canary, and rollback gates. Use only when release work is requested or already authorized.
---

# Ship with controlled authority

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane, invariants, and authorized delivery boundary.

## Preflight

1. Confirm the requested delivery boundary: local commit, branch push, PR, merge, environment deploy, or production. Do not infer the next boundary.
2. Re-read repository instructions, current branch/status, authoritative artifacts, review findings, and fresh verification evidence. If code changed after review or verification, repeat the affected gates.
3. Preserve unrelated work. Stage only approved paths. Never bypass branch protection, required checks, or reviewers.
4. Confirm versioning, migration order, secrets handling, rollback or recovery command, and post-release canary when applicable.

## Delivery

1. Create the smallest coherent commit only when authorized.
2. Push or open/update a PR only when authorized. The PR must link intent/spec/plan where used, summarize risk, list proof and limitations, and state rollback.
3. Watch required checks and review comments. Fix verified findings through the normal build-review-verify loop; do not blindly satisfy comments.
4. Keep author, reviewer, and approver distinct for Controlled work. Green automation never grants production authority.
5. Deploy only to the authorized environment with the repository's existing mechanism.
6. Run a production-relevant canary against the intended domain, service, or artifact. Compare the deployed revision with the intended revision.
7. If the canary fails, stop or use only a pre-authorized recovery runbook. Capture evidence and route diagnosis to `ai-native-debug`.
8. Record the released revision, environment, evidence, approver, and known limitations in the authoritative release system. Update state to `released` or `monitoring`.

## Completion

Report exactly what was delivered, where, at which revision, which checks passed, and what remains outside scope.
