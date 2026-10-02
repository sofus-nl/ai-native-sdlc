# Changelog

## 0.5.0 - Unreleased

- Adopted a Helix-informed checkpoint convergence loop for Standard and Controlled work: `plan.md` holds an ordered checkpoint list approved at the plan gate, and each checkpoint passes behavior, visual (UI only), and self-review gates before the next. Plan checkpoints double as the Git commit points in `checkpoints.md`.
- Controlled work adds review checkpoint mode with two context-isolated reviewers, a separate test author when available, and a human stop after checkpoint 1; a recorded `checkpoint` approval covers a stated scope.
- Added a "Reference oracle" field to `spec.md`, the `checkpoint` approval gate, and human feedback in `state.md`. Verify step 5 is now a matched-state visual gate with severity, location, and INVALID recapture. Economy orders gates cheapest first.
- Hardened checkpoint approvals: single-agent Controlled work needs a human per checkpoint, `checkpoint` approvals name the covered checkpoints and plan revision, pending approvals block resume, visual recapture is capped, test-author checks are protected, build resumes at the checkpoint in `next_action`, and the visual gate handles written oracles. Behavior-check rubric and filesystem checks now require the checkpoint list and Reference oracle, and the feature case scripts one plan-approval turn.
- Fixed the behavior checker crashing on non-UTF-8 files instead of reporting a failure, and the version checker validating an older changelog heading when the top heading was malformed; CI now also runs the checker regression test.
- Fixed routing gaps found by the first cross-host behavior run: bounded features and plan requests are Standard or higher, Standard work without `spec.md` routes to shape, plan-only requests may draft a plan without accepting upstream artifacts, Standard and Controlled plans require `spec.md`, and paired-evidence fields apply to every model qualification claim (verify now points to them). The model-override fixture now states requirement strength and baseline.
- Added the `payment-build` behavior case: a Controlled change built in two checkpoints with scripted approval turns, exercising the stop after checkpoint 1, checkpoint review, and scoped approvals. Its first run showed that authorization to implement was read as gate approval (Codex) and that the blocked state and `checkpoint` approval went unrecorded (Claude Code); the router, build, and artifact contract now say so explicitly.
- An approval now covers only artifact revisions the human could read when deciding; a reply given before an artifact exists never approves it. Both hosts had recorded one early reply as approval of a specification and plan written afterward. The payment-build scripted reply no longer names the artifacts it approves, and the rubric fails approvals of later-written artifacts. Approval timestamps must come from a clock command run when recording; Claude Code had written times ahead of the real clock. One reply that approves several readable artifacts now records one approval per gate, and Controlled work always records a `design` approval of `spec.md`; the payment-build checker requires all four approval gates. The router now tells agents to run a clock command before recording any approval, because Claude Code read the clock in some runs but not others; the checker fails date-only approval times. Behavior checks now request an exact model ID, because the host's `sonnet` alias moved to a different model between runs.
- Hardened Controlled work for `claude-sonnet-5-5`, which built a payment change with no lifecycle files in one run and, in another, used one reviewer per checkpoint and skipped final verification. The router now says size never lowers the lane, that Controlled work edits no code before a recorded `plan` approval whatever the task size or general file-avoidance instructions, and that the next skill is invoked, never done from the router. Controlled work without an approved `intent.md` routes to shape, and plan no longer writes a missing specification itself. The README lists `claude-sonnet-5-5` as not yet qualified for Controlled work. Build now names the two-reviewer checkpoint gate inline, requires invoking the review skill rather than only a reviewer agent, and forbids reporting completion before verification. The payment-build checker now requires a final `status: verified`.
- Added an optional Claude Code guard hook (`hooks/edit_guard.py`, registered from `.claude-plugin/hooks.json`). In a session using this plugin it denies file writes until the lane is stated and the required approvals are recorded in `state.md` (`plan` for Standard; `intent`, `design`, and `plan` for Controlled), and it blocks ending a Standard or Controlled turn once while `status` is `building` or `reviewing`. It needs `python` on PATH, is inactive without it, and does not apply on Codex. See ADR-003.
- Fixed a regression from the Controlled routing hardening: a plan-only request on Controlled work stopped at the intent gate and produced no specification or plan. Router and shape now draft `spec.md` and `plan.md` for plan-only requests, with nothing accepted. The full 12-case suite found it; `payment` had not been re-run after the hardening. The suite also showed `payment-build` asking for an extra approval after the last checkpoint in 2 of 5 runs; build now says the stop after checkpoint 1 is the only mandatory approval stop.
- The router now counts a risk signal that cannot be ruled out after reading the relevant code as present, so uncertain work cannot fall into the Fast lane. TypeSafe Jev was evaluated for routing and not adopted (ADR-002).
- Fixed lane consistency: plan stops without required artifacts or plan approval, shape writes `intent.md` for Standard work only when ambiguous, and Fast excludes cross-service effects in the operating model.
- Added scoped commit/push checkpoints to planning, building, and shipping; separated branch sharing from integration/release gates and preserved staged-snapshot, outgoing-history, and authorization checks.
- Integrated SemVer 2.0.0 into project release planning, verification, and shipping through an on-demand reference, preserving existing repository policy and publication authority.
- Declared the plugin compatibility contract and SemVer release policy; added automated version-format, manifest-alignment, and changelog checks.
- Assigned the model-selection addition a new minor version rather than reusing 0.4.0. This entry is release preparation, not evidence of publication or cross-host verification.
- Added on-demand, task-qualified model selection through the shared economy policy, preserving baseline fallback, host-control boundaries, complete-cost accounting, and existing verification gates.
- Added three read-only model-selection scenarios and checker regressions for substitution, qualification gaps, and retry costs; live cross-host behavior and model-quality qualification remain untested.
- Recorded the model-routing second-pass review, qualifying model tiers, aggregate parity, full-attempt cost, and requested-versus-observed execution identity.

## 0.4.0 - 2026-09-05

- Added conditional delegation, host-aware context selection, bounded handoffs, and stale-result checks to the shared economy policy and plan/build/review skills.
- Preserved fresh integrated-state verification and authorization gates.
- Extended behavior checks for independent investigations, shared-state ownership, and stale worker results, with paired-evaluation guidance.

- Recorded an adversarial review of the sub-agent optimization proposal, preserving verification gates and qualifying evidence transfer and host context behavior.

- Added five disposable behavior fixtures, a filesystem checker, and a transcript-review rubric for release checks.

- Added public installation, usage, troubleshooting, and contribution documentation.
- Prepared the shared Claude Code and Codex package for sofus-nl/ai-native-sdlc.

## 0.3.0 - 2026-09-05

- Added Claude Code plugin and local marketplace manifests.
- Reused the same skill tree across Codex and Claude Code to prevent drift.

## 0.2.0 - 2026-09-04

- Added a shared solution ladder, context budget, and concise output contract.
- Added complexity budgets to plans and a dedicated simplicity review pass.
- Added explicit stop conditions after acceptance and honest token measurement rules.

## 0.1.0 - 2026-09-04

- Added a risk-sized AI-native lifecycle router.
- Added shape, plan, build, debug, review, verify, ship, and operate skills.
- Added compact artifact, state, gating, and provenance contracts.
