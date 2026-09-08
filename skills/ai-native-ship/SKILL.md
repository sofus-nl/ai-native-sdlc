---
name: ai-native-ship
description: Perform authorized Git delivery or release work through commit, branch push, PR, CI, deployment, and canary gates. Distinguish sharing checkpoints from merge and release readiness.
---

# Ship with controlled authority

When invoked directly, first read `../ai-native-sdlc/SKILL.md` and confirm the lane, invariants, and authorized delivery boundary.

## Preflight

1. Confirm the requested delivery boundary: local commit, branch push, PR, merge, environment deploy, or production. Apply `../ai-native-sdlc/references/checkpoints.md`; do not infer the next boundary.
2. Re-read repository instructions, current branch/status, authoritative artifacts, and evidence required for that boundary. Sharing an authorized working branch can precede remote CI or final review; integration and release require their applicable gates. If code changed after review or verification, repeat the affected gates before claiming readiness.
3. Preserve unrelated work. Stage only approved paths. Never bypass branch protection, required checks, or reviewers.
4. For versioned releases, apply `../ai-native-sdlc/references/semver.md`: verify the proposed bump against the public contract and published baseline, align version sources and release notes, and reject reuse of a released version. Confirm migration order, secrets handling, rollback or recovery command, and post-release canary when applicable. A commit-only or push-only request does not authorize a release.

## Delivery

Perform only the steps applicable to the authorized boundary; stop when that boundary is complete.

1. Create the smallest coherent commit only when authorized.
2. Push or open/update a PR only when authorized. The PR must link intent/spec/plan where used, summarize risk, list proof and limitations, and state rollback.
3. Watch required checks and review comments. Fix verified findings through the normal build-review-verify loop; do not blindly satisfy comments.
4. Keep author, reviewer, and approver distinct for Controlled work. Green automation never grants production authority.
5. Deploy only to the authorized environment with the repository's existing mechanism.
6. Run a production-relevant canary against the intended domain, service, or artifact. Compare the deployed revision with the intended revision.
7. If the canary fails, stop or use only a pre-authorized recovery runbook. Capture evidence and route diagnosis to `ai-native-debug`.
8. Only after an actual release, record its revision, environment, evidence, approver, and known limitations in the authoritative release system, and update state to `released` or `monitoring`. For commit, push, or PR-only work, report that boundary and stop without marking a release or performing later delivery steps.

## Completion

Report exactly what was delivered, where, at which revision, which checks passed, and what remains outside scope.
