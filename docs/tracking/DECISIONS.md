# Decisions

## ADR-001: Adopt the Helix checkpoint convergence loop, lane-proportional (2026-09-28)

### Status

Accepted

### Context

Shopify's [Helix](https://shopify.engineering/helix) does not expect a correct first attempt. It forces convergence instead: work is split into small, human-approved checkpoints, and each checkpoint must pass behavior tests, a matched-state visual review, and two isolated code reviewers before the next one starts. Human feedback is kept and applied to later checkpoints, and humans scrutinize early checkpoints most closely.

Before this change the plugin already ran focused tests and a self-check per task, and it ran one independent review on the full diff. What it lacked:

- a plan summary short enough for a human to approve quickly;
- a structured visual gate;
- per-slice independent review for high-risk work;
- a test author separate from the implementer;
- human feedback carried forward to later work.

### Decision

- **Standard and Controlled:**
  - `plan.md` holds an ordered checkpoint list, which the human approves at the plan gate.
  - Each checkpoint passes three gates, cheapest first: behavior, visual (UI only), and self-review against acceptance IDs.
  - Human feedback goes into `state.md`, and later checkpoints read it.
  - `spec.md` names a Reference oracle for gates to compare against.
- **Controlled only:**
  - Each checkpoint also gets two context-isolated reviewers (review checkpoint mode), and both must approve.
  - A separate test author writes the checks when the host supports it.
  - Build stops for human approval after checkpoint 1. After that, a recorded `checkpoint` approval either pre-authorizes the rest or keeps approval per checkpoint.
- **One checkpoint concept:** plan checkpoints are also the Git commit and share points defined in `skills/ai-native-sdlc/references/checkpoints.md`. There is no second checkpoint system.
- **Fast:** unchanged.
- **Our addition, not Helix's:** prefer a different model family for the second reviewer when the host offers one.

### Consequences

- The human sees a short, ordered checkpoint list before any code is written.
- Controlled work costs more review per change, in exchange for catching defects per slice instead of at the end.
- Standard work adds no reviewer passes. The added cost there is the checkpoint list and, for UI work, the visual gate.
- None of this is enforced by tooling. It is instructions only, like the rest of the plugin.

### Alternatives rejected

- **Full loop, including per-checkpoint independent review, on all Standard work.** It multiplies review cost by the number of checkpoints, and it contradicts the operating model's statement that independent agents are "not ceremony requirements".
- **Controlled-only adoption.** Everyday work would get neither a checkpoint list nor a visual gate.
- **Human approval of every Controlled checkpoint by default.** It adds N interrupts on top of the existing gates. A single stop after checkpoint 1 captures Helix's early scrutiny.

## ADR-002: Evaluate TypeSafe Jev for routing; not adopted (2026-09-28)

### Status

Accepted

### Context

TypeSafe's Jev (`typesafe/jev-1.13` on OpenRouter) is a non-generative decision model built on the ["System One" pattern](https://docs.typesafe.ai/concepts/how-to-build-with-system-one). It takes JSON state and typed questions and returns typed answers with calibrated probabilities. A companion product, Jev Router, picks the LLM and reasoning effort for each request. We asked whether either could improve the plugin, starting with the router skill.

Facts we checked on 2026-09-28:

- Jev launched in early access on 2026-09-15 and is hosted only.
- Its context window is 32k tokens, text only.
- We found no data-retention or privacy terms.
- Jev Router does not disclose its candidate models or its routing logic.
- The published benchmarks are run by the vendor.

### Decision

Do not call Jev or Jev Router from the plugin. Adopt one System One idea: when an answer is uncertain, escalate it instead of guessing. The router now says that a risk signal the agent cannot rule out after reading the relevant code counts as present. The agent therefore can no longer guess its way down to the Fast lane.

Reasons:

1. **Routing costs little today.** The host model already holds the request and the repository context when it chooses a lane. A Jev call would save almost nothing, and it would add a network round trip.
2. **It breaks the product shape.** The plugin is Markdown skills with no runtime. Calling Jev would need a script, an OpenRouter key for every user, and network access from every host.
3. **Data would leave the machine.** Request and repository content would go to an early-access third party with no published retention terms. `model-selection.md` forbids cross-provider execution without an authorized runtime and data scope.
4. **Jev Router cannot meet our own qualification rule.** That rule needs the exact model and version, paired evidence, and a baseline. The router's model pool is undisclosed.

The rest of System One is already in place: deterministic rules stay deterministic, lanes are chosen from atomic risk signals with the highest signal winning, and the human owns judgment gates.

### Revisit when

- Jev publishes retention terms and independent evaluations exist.
- The plugin gains an optional runtime.
- A product built with the plugin needs high-volume narrow classification. That is Jev's real fit, and there Jev would be a product dependency, not a plugin dependency.

## ADR-003: Enforce Standard and Controlled gates with a Claude Code hook (2026-09-29)

### Status

Accepted (2026-09-29). Trialed on `claude-sonnet-5-5`; also checked on Codex, where it stays inactive.

### Context

On `claude-sonnet-5-5`, which the `sonnet` alias in Claude Code resolved to from 2026-09-29, the plugin's instructions did not reliably hold. In the `payment-build` behavior case, 4 of 4 early runs failed: some built a payment change with no lifecycle files ("the task was fully specified and small"), and others dispatched one reviewer agent instead of the review skill and never verified. Rewording the router, plan, and build skills raised compliance to about 1 run in 2, and one wording attempt made both models worse. Removing the user's global `CLAUDE.md` did not change the result, so the model itself is the cause. More wording rounds cost about $10 each and give no guarantee.

### Decision

Ship `hooks/edit_guard.py` as a Claude Code plugin hook, registered from `.claude-plugin/hooks.json` through the Claude manifest. It runs only in a session that has invoked an `ai-native-sdlc` skill.

- **Before a file write** (Edit, Write, MultiEdit, NotebookEdit, or a shell command that writes): deny when the lane has not been stated. Deny for Standard work until `state.md` records a `plan` approval, and for Controlled work until it records `intent`, `design`, and `plan` approvals. Writes under `.sdlc/` are always allowed. Fast work is never blocked.
- **At the end of a turn:** for Standard or Controlled work at `status: building` or `reviewing`, block the stop once and tell the agent to run review and verification, or to set `status: blocked` if it needs the human. A second stop passes, so the agent can always hand back.
- **Failure mode:** if `python` is missing or the hook errors, the guard is inactive and work is not blocked.

The hook is registered from `.claude-plugin/` and not from the default `hooks/hooks.json`, because Codex loads that default path and `${CLAUDE_PLUGIN_ROOT}` may be unset there. Codex has no equivalent guard.

### Consequences

- In trials, all 8 guarded `claude-sonnet-5-5` runs recorded the approvals before any code, and the 4 runs made after the end-of-turn check all reached `verified`. Small tasks kept their lanes: `typo` created no lifecycle files and `feature` stopped for plan approval, on both models.
- The guard does not enforce a separate test author or two reviewers. In the last 4 runs on `claude-sonnet-5-5`, 2 skipped the separate test author. That gap stays instruction-only.
- The plugin gains its first non-Markdown file, and Claude Code users need `python` on PATH for the guard to work. It is one file, about 100 lines, with a unit test.
- Detecting writes made through shell commands is a heuristic. A command that writes through a program the guard does not list is not caught.
- The guard reads Claude Code's transcript format, so it does nothing on Codex.

### Alternatives rejected

- **More instruction rewording.** Costly, and compliance stays probabilistic.
- **Marking `claude-sonnet-5-5` unsupported and stopping.** The README label already does this, but it leaves default-Sonnet users without protection.
- **A model-judged hook** that asks a small model whether an edit is high-risk. It cannot read `state.md` from a yes/no prompt, and the deterministic check already covers the failures seen.

## ADR-004: Add STE-informed clarity rules as wording only (2026-10-07)

### Status

Accepted (2026-10-07).

### Context

Specification acceptance criteria, plan steps, evidence, and PR text are approved by humans and executed by agents. The asd-ste100-skill repo offers "80% ASD-STE100" structural rules plus a regex linter. No behavior run or incident on record shows vague wording causing a failure; all recorded failures were gate compliance. The change is preventive.

### Decision

Add clarity rule sets to artifact-contracts.md and economy.md as wording only. No new skill, file, or script. Two rule sets: acceptance criteria state one testable condition each and avoid `should`, `appropriate`, `as needed`, `etc.`, `TBD`, `and/or` (quoted UI copy and code exempt); output budget in economy.md: one action per step in active voice, one term per thing, never upgrade a hedge (`may`, `likely`, `not verified`) to a fact, risky steps marked `WARNING:`/`CAUTION:` with command first and reason second.

### Consequences

Compliance is instruction-only and therefore probabilistic (see ADR-003). No new runtime dependency. Verify and ship already cover limitations and rollback, so they are unchanged.

### Alternatives rejected

- **(a) An agent-run linter script** — an agent in a user's repository cannot reliably resolve the plugin's script path, it would add a Python runtime dependency on Codex, and an agent-invoked check holds no better than wording (ADR-003); an advisory linter was first chosen, then dropped after an independent review.
- **(b) The ASD-STE100 approved-word dictionary** — domain terms must stay.
- **(c) Hard word caps of 20/25 words** — precise acceptance criteria need room.
- **(d) The source repo's diagram, HTML, and video output tiers** — outside an SDLC plugin's scope.

### Revisit when

A behavior transcript shows a vague acceptance criterion or an upgraded hedge passing a gate. Then add a non-blocking check to `hooks/edit_guard.py` on writes to `.sdlc/changes/*/spec.md`.

## ADR-005: Absorb unlazy completion rules as wording only (2026-10-10)

### Status

Accepted (2026-10-10).

### Context

Agents stop short: they leave placeholders, drop parts of multi-part requests, and report unmeasured numbers. The unlazy repo (MIT, Leonxlnx) addresses this with acceptance gates written before work, a Depth Tree of leaf ledgers, a four-pass leaf loop, a final-report audit, and an optional Claude Code Stop hook backed by about 400 KB of Node scripts. This plugin already writes acceptance criteria before building, treats a worker report as unproven, requires fresh evidence, and nudges once at Stop for unfinished Standard and Controlled changes. The remaining gaps were: no explicit ban on placeholders or deferred remainder, verify re-read the acceptance map but not the original request, no met/unmet report, and reported numbers were not re-measured.

### Decision

Add the missing rules as wording only, in original text: one router invariant (finish every in-scope part; no placeholders, stubs, `TODO`s, elided code, or deferred remainder; minimal means least code per part, not fewer parts; report unfinished parts as unmet), a router output rule (met/unmet per part; re-measure numbers or label them `not measured`), a completeness clause and defect hunt in build self-review, and an original-request re-read with met/unmet counts in verify.

### Consequences

Compliance is instruction-only and therefore probabilistic (see ADR-003). The rules apply to every lane, including Fast. No new runtime dependency, and the "No third-party code is bundled" notice stays true.

### Alternatives rejected

- **(a) Vendoring unlazy's gate-check, dispatch, and stop-hook scripts** — bundles third-party code, adds a surface where agents approve arbitrary shell `CHECK:` commands, and duplicates `ai-native-verify`.
- **(b) A Stop hook that blocks several times until gates are met** — loop risk, and the hook-guard design is still an open decision; the existing one-nudge `decideStop` stays.
- **(c) The Depth Tree with per-leaf ledgers** — ceremony that overlaps the existing plan checkpoints.

### Revisit when

A behavior transcript shows a dropped request part or a placeholder passing verify. Then add a behavior case to `scripts/behavior_check.py`.
