# Changelog

## 0.6.2 - 2026-10-31

- Verification: hook-only release, so the 12-case behavior suite did not run. `scripts/test_edit_guard.py` covers each fix below. A replay fed the logged hook events of three desktop sessions from one private project (2026-10-17 to 2026-10-30, all on 0.6.1) through both versions. It read today's `state.md` files, not the files as they were then.
  - All 8 logged write denials: 0.6.1 still denies all 8, and 0.6.2 allows all 8.
  - All 24 logged Stop blocks: 21 came while a background agent or command was still running, and 0.6.2 allows those. The other 3 had nothing running, and 0.6.2 still blocks them once. The replay infers running work from the transcript (launched, with no completion notification yet), not from a real `background_tasks` field.
  - 212 sampled writes that 0.6.1 allowed: 0.6.2 denies 1. It is a redirect to a temp log in a session that had not stated its lane; 0.6.1 had taken the lane from another change's `state.md`.
  - Not run: a live Claude Code session on 0.6.2. Codex does not load the hook.
- Fixed: the gate check read every `.sdlc/changes/*/state.md`, so one approved change unlocked writes for all work, and a stale change could force its lane on unrelated work. The hook now reads only the active change: the `state.md` that this session last wrote, through an edit tool or a shell command. If the session wrote none, it is the `state.md` that the session last read. Reading another change's `state.md` for context no longer switches the active change. Approvals count only from entries of the `approvals:` list that start with `gate:`. `current_gate: plan`, notes below the list such as "asked at the gate: plan", and `decision: rejected` entries no longer pass a gate.
- Fixed: any change's `lane:` could override the lane stated in chat. The stricter of the stated lane and the active change's recorded lane now applies, so stating a lower lane never clears a gate.
- Fixed: the hook was active in every session where the plugin was installed, because Claude Code writes the names of all installed skills into each transcript. It now activates only after a `Skill` call to an `ai-native-sdlc:` skill or a typed `/ai-native-sdlc:` command.
- Fixed: the hook looked for `.sdlc` under the shell's current directory, which follows every `cd`. All 8 logged denials came from a subdirectory (`out/`, `node_modules/`, or inside `.sdlc/`). The hook now uses the absolute `state.md` path from the transcript. For a relative path, it walks up from the current directory to the nearest `.sdlc`, then tries `CLAUDE_PROJECT_DIR`.
- Fixed: the Stop hook blocked while background work ran, and agents set `status: blocked` to get past it, which recorded false blockers. The hook now allows the stop while Claude Code reports background tasks, checks only the active change, and matches the `status:` and `lane:` keys in any case. Its message now says that `blocked` means waiting on a human only.
- The write denial now names the active change's `state.md`, or says that this session has read or written none.
- Known limits:
  - A long-running background shell, such as a dev server, also suppresses the Stop nudge.
  - Edits that belong to other work are still checked against the session's active change.
  - An inline approval list (`approvals: [{gate: plan}]`) is not read. Write one entry per line, as `artifact-contracts.md` shows; all 123 real state files that list approvals already do.
  - A `state.md` written by a separate script file (`python fix_state.py`) counts as read, not written. A blank line inside the `approvals:` list ends the list, so later entries are not read.
  - Until a `state.md` is active, the last lane named in chat wins, so "Lane: Controlled. Fast lane does not apply." reads as Fast.
  - In one desktop session, an assistant message that stated the lane did not reach the transcript file the hook reads, so the hook denied writes. The 2-second re-read does not cover that case.

## 0.6.1 - 2026-10-15

- Verification: hook-only release, so the 12-case behavior suite did not run (`docs/behavior-checks.md` requires it for skill-instruction changes). Instead, headless Claude Code 2.1.300 sessions with `claude-sonnet-5-5` replayed the reported failure on a typo fixture: the agent writes "The lane is Fast." and then edits. On 0.6.0 the hook blocked every edit (4 denials) and the agent gave up. On 0.6.1, 6 of 6 sessions edited with no denial. Without the re-read below, 3 of 4 sessions were denied once. Brief mode is not available in headless sessions, so the `SendUserMessage` path is covered by unit tests only. Codex does not load the hook and was not re-run.
- Fixed the guard hook denying file changes with "State the lane" after the lane was stated, in three cases:
  - Brief mode: the lane was stated through `SendUserMessage` (alias `Brief`). The hook read only assistant text blocks, so it never saw the statement. It now also reads the `message` of those tool calls.
  - Phrasing: "Lane is Fast" or "Lane for this: Fast" did not match, because only punctuation was allowed between "lane" and the lane name. Up to 20 characters on the same line are now allowed, the same as for "Fast lane".
  - Same message: when the lane statement and the tool call were in one assistant message, the statement could reach the transcript after the hook read it. When no lane is found, the hook now re-reads the transcript every 0.1 s for up to 2 s before denying. In the sessions above the statement arrived within 0.7 s. A write with no stated lane is now denied after that 2 s wait.
- The denial now gives an example of an accepted statement ("Lane: Fast"), so a retry does not depend on guessing the pattern.

## 0.6.0 - 2026-10-10

- Verification: the full 12-case behavior suite ran with independent transcript review on Claude Code 2.1.296 with `claude-sonnet-5-5` and Codex 0.161.0 with `gpt-6.1-sol` (reasoning effort low). Results were 11/12 and 12/12. All filesystem and executable acceptance checks passed. `claude-sonnet-5` was not re-run.
  - Claude Code `payment` failed: the plan-only Controlled draft did not name the human approval needed after checkpoint 1. In a paired run on `claude-sonnet-5-5` the gap appeared in 1 of 3 runs on 0.5.1 and in 3 or 4 of 4 runs on 0.6.0 before the fix below, and in 1 or 2 of 4 runs after it. Small samples: a direction, not a rate. Codex named the approval in 2 of 2 runs after the fix.
  - Run limits: both hosts ran with permission prompts and sandboxes off in disposable fixture folders, because the Windows Codex sandbox blocked or hung every command. Codex ran from an isolated `CODEX_HOME` with the plugin installed from GitHub; user-level skills in `~/.agents/skills` stayed discoverable but no scored session invoked them. The user's global CLAUDE.md stayed loaded on Claude Code.
  - Observed: build and verify reports listed met and unmet counts (for example "4 met, 0 unmet"), and no changed file had placeholders. Met/unmet marking was uneven in Fast and read-only cases, and in two cases the final report did not re-measure figures it quoted from fixtures or workers.
- Fixed: the router's plan-only clause now lists the Controlled approval after checkpoint 1 among the approvals still needed, because `ai-native-plan`, which states that rule, was skipped in the failing run.
- Added completion rules informed by unlazy (MIT License). Wording only; no scripts or hooks bundled. See ADR-005.
  - Router invariant: finish every in-scope part of the request, with no placeholders, stubs, `TODO`s, elided code, or silently deferred remainder. Minimal means the least code per part, not fewer parts. A part that cannot be finished is reported as unmet with its reason.
  - Router output: mark each requested part met or unmet, and re-measure every reported number or label it `not measured`.
  - Build: each checkpoint is implemented completely, and self-review also hunts defects, placeholders, and unhandled cases.
  - Verify: step 8 re-reads the original request and maps every requested part to a supported claim or a reported unmet item; the evidence report ends with met and unmet counts.

## 0.5.1 - 2026-10-08

- Verification: the full 12-case behavior suite ran with independent transcript review on three hosts: Claude Code 2.1.294 with `claude-sonnet-5` and `claude-sonnet-5-5`, and Codex 0.160.1 with `gpt-6.1-sol`. Codex used `gpt-6.1-sol`, not the `gpt-6-astra` used for 0.5.0. Results were 9/12, 12/12, and 12/12. All filesystem and executable acceptance checks passed. Reviewers attributed none of the three `claude-sonnet-5` failures to this release:
  - `typo` skipped its diff check, a known 0.5.0 limit.
  - `payment` did not name the human checkpoint-1 approval still needed. An earlier run with the same gap was scored as a pass.
  - `payment-build` skipped the separate test author and dispatched reviewers directly. The 0.5.0 limit "the separate test author is skipped in some Claude Code runs" still applies.
- Earlier runs of this release, before the fixes below, scored 10/12, 11/12, and 11/12, and `qualification` failed on every host.
- The final checklist scoping and the "model cost" wording were checked only on Claude Code. On Codex the scoping check could not run, because Windows cancelled the elevated sandbox helper (error 1223).
- The acceptance-criteria rule produced no banned terms, but some `payment-build` criteria still bundle several conditions. No run used `WARNING:` or `CAUTION:`, and no run read `economy.md`, so the economy.md rules are untested.
- Added clarity rules to artifact-contracts.md and economy.md, informed by ASD-STE100 Simplified Technical English via asd-ste100-skill (MIT License). Wording only; no linter or compliance tool. See ADR-004.
- Fixed the `qualification` behavior case, which failed on every host. The model-selection reference now lists the evidence a model qualification claim needs as a checklist, and an assessment of a model qualification claim reports each item as present or missing. The list is skipped when no one claims a model is qualified, because some runs had attached it to `model-override`. The router now reads that reference before answering any model-selection, qualification, or cost question, including read-only work; one run had skipped it.
- The router skill now also activates for read-only reviews of model selection, model qualification claims, or model cost, and whenever the user asks to use ai-native-sdlc. In 3 of 4 earlier Claude Code runs, `model-override` had skipped the plugin as read-only. After the change it activated in 8 of 8 runs across `claude-sonnet-5` and `claude-sonnet-5-5`. Six unrelated cost questions about cloud hosting and budgets were also tried across both models, and none activated the plugin.
- Fixed the guard hook leaving the transcript file open after reading it (`ResourceWarning` in `hooks/edit_guard.py`).

## 0.5.0 - 2026-10-03

- Verification at release: the full 12-case behavior suite ran on Claude Code (`claude-sonnet-5`) and Codex (`gpt-6-astra`) with independent transcript review, plus targeted re-runs after the final fixes. Known limits: `claude-sonnet-5-5` is not yet qualified for Controlled work; the separate test author is skipped in some Claude Code runs; the guard hook is Claude Code only; on Claude Code, `typo`, `payment`, `model-override`, `qualification`, and `cost-retry` missed parts of the rubric in the last full suite run; the visual gate and workspace marketplace import were not tested.
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
- Fixed a Codex failure of the `feature` case: a Standard-lane task wrote and verified code before the human approved the plan, apparently because the Controlled-only hard stop read as optional for Standard. The router now applies the no-code-before-plan-approval rule to Standard and Controlled work. Shape now hands a plan-only request to plan in the same turn; one `payment` run had stopped after writing the specification.
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
