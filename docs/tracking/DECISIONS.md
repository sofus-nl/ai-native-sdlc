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

### Amendment (0.6.2, 2026-10-31)

A private review of two weeks of session logs found that the hook did not do what this ADR decided. All 8 logged write denials and 21 of 24 Stop blocks were false, and approvals from one change unlocked writes for all other work. The decision now reads as follows:

- **Which `state.md` counts:** only the active change. That is the `state.md` that the session last wrote, through an edit tool or a shell command, or, if it wrote none, the one it last read. Approvals count only from entries of the `approvals:` list that start with `gate:`. The stricter of the lane stated in chat and the active change's recorded lane applies.
- **When the hook runs:** only after a `Skill` call to an `ai-native-sdlc:` skill or a typed `/ai-native-sdlc:` command. Before 0.6.2, the list of installed skills in every transcript made the hook run in every session.
- **Where `.sdlc` is:** the absolute path from the transcript, or else the nearest `.sdlc` above the current directory, or else `CLAUDE_PROJECT_DIR`.
- **At the end of a turn:** the stop passes while Claude Code reports background tasks (the Stop input's `background_tasks` field). `blocked` means waiting on a human only.

Rejected: a new `waiting` status in `state.md`. It changes the artifact contract (a minor version), and the host's `background_tasks` field already tells the hook that the session is paused.

### Amendment (0.7.1, 2026-11-07)

A replay of about 15,000 shell commands from private session logs showed that the hook counted a quarter of them as project writes. Independent reviewers read all but a few dozen of the commands that this amendment stops counting; every one that was a project write came from inside a script (`os.remove`, a helper module), which no version detects by rule. Two independent reviews of the code then found holes that the first version of this amendment had opened; each is closed and tested. What counts as a gated shell write now reads as follows:

- **Scratch files pass:** a redirect to a temp folder (`$TEMP`, `$TMP`, `$TMPDIR`, `/tmp`, `/var/tmp`, `/dev`) passes, unless the project itself lies under it (the project is the working directory, `CLAUDE_PROJECT_DIR`, and their parents that hold `.git` or `.sdlc`). Every other path outside `.sdlc/` counts as a project write, including a sibling clone of the repository: a wider "outside the project" rule was tried first, and a review of real commands found nine writes into sibling clones that it let through.
- **Lifecycle writes:** a move, removal, copy, or `sed -i` whose every target is under `.sdlc/` passes. A path with `..` never counts as under `.sdlc/`.
- **Where a target points:** a variable is resolved from the one assignment, in command position, that precedes its use; `$TEMP`, `$TMP`, and `$TMPDIR` come from the environment. A relative target follows a `cd` earlier in the command only while every directory change in the command is a plain one at the start of a segment and nothing runs in a subshell, a group, or another program; otherwise, and after `cd -` or an unknown variable, the target is a plain relative path, which counts as a project file. The hook assumes a `cd` succeeded.
- **Quoted arguments are data:** a `>` or a command name inside a quoted argument is not a write, unless something runs that argument (`bash -c`, `eval`, `iex`, command substitution, `os.system(`, `subprocess.run(`), the quoted word is the command itself, or a quote is left unpaired. A comment line or an escaped quote that holds a quote character turns hiding off for that command, so an apostrophe in a comment cannot hide the commands after it.
- **Sub-agents:** Claude Code calls the hook for a sub-agent's tool calls with the parent session's transcript, so the same lane and approvals apply to them.

Deferred: an environment variable that lets the human switch the guard off when it is wrong. It adds to the documented interface, so it needs a minor version.

### Amendment (0.7.3, 2026-11-08)

A manual-harness run of 0.7.2 showed a false denial of a lifecycle write after `cd <project> && ... && cd .sdlc/changes/<slug> && D=$(date +%F) && cat > spec.md`. The cause was the `$(date +%F)`, not the absolute `cd`: any parenthesis stopped `cd` following. A `$(...)` that holds no directory change and no nested parenthesis now leaves the following on, because it cannot move the shell; its inner commands are still scanned like any segment. Every other subshell, group, and nested shell still stops it, and so does a `$(...)` in quotes.

### Amendment (0.8.0, 2026-11-14)

A review against 2026 field evidence and popular guard projects questioned the failure mode. Guards that protect against damage (cc-safety-net, failproofai) deny when they fail; guards that steer a workflow (tdd-guard, Anthropic's hookify) let the action through. This guard steers a workflow, so the 2026-09-29 failure mode stays, with one change:

- **A failure after the session is known to use the plugin denies the write.** Once the hook has read the whole transcript and seen the plugin invoked, an error while it checks the lane or the approvals returns a denial that names the error. Before 0.8.0 that error let a gated write through.
- **Every other failure still blocks nothing:** unreadable hook input, an error while reading the transcript or the command, a missing `python`, a timeout. For the first three the hook exits 1 and prints `ai-native-sdlc guard is inactive for this call`, which Claude Code shows as a hook error notice. A transcript file that cannot be opened passes without a message, as before.
- **Why a transcript error does not deny:** the transcript only grows. One entry the hook cannot parse would deny every later write of that session, Fast work included. An independent review of the first draft, which did deny there, reproduced that lockout.
- **A failure at the end of a turn never blocks the stop.**

Rejected: `onFailure: "block"` in `hooks.json` (Claude Code 2.1.295 or later). It also covers a missing `python` and a timeout, but it applies to the hook in every session, so a machine without `python` could change no file in any project, including sessions that never use the plugin.

Rejected: denying by lane ("fail closed for Standard and Controlled only"). The lane comes from the transcript and `state.md`, which the hook has not read when the input is unreadable or the transcript read fails.

**The verify gate (same release).** Two new behavior cases, `gamed` and `weakened`, start at `status: reviewing` with a defect that passes the fixture's check. On 0.7.3 the agent found and fixed the defect in every one of 9 runs, and in every one it then wrote `status: verified` itself: it never invoked `ai-native-verify`, and nothing reviewed its fix. The router's rule ("invoke review on the full diff, then verify, before claiming a code change complete") is instruction text, and the end-of-turn check passes once the status says `verified`. So the hook now checks the write that makes the claim:

- **Rule:** in Standard and Controlled work, a write that puts `status: verified` into a change's `state.md` is denied unless this session invoked `ai-native-verify`. If the session changed code before that call, an `ai-native-review` call must lie between the last such change and the verify call.
- **Every denial has an exit the agent can reach:** the reason names the skill to invoke. In 6 of 6 runs on the released hook the agent finished the case; in the 5 runs with a denial it cleared each one by invoking the named skill. On two drafts, 2 of 12 runs ended at `status: blocked` instead: one draft counted a denied command as a code change, and the other asked for review when only verify was missing. Only tool calls that ran count now (a shell command that ran and then failed still counts; a refused one does not), and the reason names the next skill to invoke.
- **A code change after verify started does not count,** because verify reverses a fix to prove that a check detects the bug, then restores it.
- **Not checked:** Fast work, a change with no lane, a command that only reads `state.md`.

- **The claim is a change of status.** An edit is replayed against the file: changing only the status word counts, and rewriting or closing a change that is already `verified` does not. An independent review of the first draft showed that the draft denied ship's close of a verified change in a later session, and any rewrite that kept the status line.
- **A recorded claim uses up the verify before it.** A fix made after `status: verified` was written needs review and verify again. The same review showed the draft let that fix through. A write the hook denied recorded nothing and does not count; an eval run showed a later draft counting it and naming the wrong skill.

Known limits: the hook reads only this session's transcript, so a verify or review from an earlier session or from inside a sub-agent does not count, and a code change made by a sub-agent is not seen; the agent runs the skills again, or the human edits `state.md`. A code change after the last verify call and before the first claim is not checked, and neither is one whose result the transcript no longer holds, because it cannot be told apart from verify's own reversal. Any shell write to a project file between review and verify counts as a code change and costs a second review. For shell commands the check reads literal text, so a command that writes the status another way is not caught.

Rejected: more wording. A sentence added to the review skill for these defects was removed again, because 0.7.3 already found them in 9 of 9 runs.

Rejected: checking at the end of the turn. The claim is already written by then, and a second stop always passes.

### Amendment (0.9.0, 2026-11-14)

Two reviews of 0.8.0 and a probe of Claude Code 2.1.319 showed that the transcript is the wrong source for the verify check. Sub-agent tool calls are not written to the parent transcript, so a build worker's code change was never seen. The transcript is written after the hook runs for calls in the same message. Which shell command wrote code was a guess from its text. Anthropic's hooks reference says the transcript "may lag the in-memory conversation", and OpenAI's says the format "isn't a stable interface for hooks".

- **The hook keeps its own record.** It runs after each `Skill` call and for a typed skill command, and appends the skill's name and a fingerprint of the project files to a file per session in the plugin's data folder. Only skills of this plugin that the main agent invoked are recorded. The probe showed that this event arrives before the next tool call starts, also within one message.
- **"Did code change" is a comparison of files, not of commands.** The fingerprint holds a content hash per file outside `.sdlc/` that Git does not ignore. The check asks whether the last verify started from the files the last review saw. The first draft hashed the difference from the last commit; an independent review showed that any commit then made changed code look reviewed, and the build skill commits each checkpoint.
- **A denial names the changed files.** Output that a test run rewrites would otherwise deny every round with no way for the agent to find the cause.
- **A claim counts once the state file shows it.** The hook notes a `status: verified` write it let through and records it at the next call if the file then holds that status.
- **Still from the transcript:** the lane stated in chat, whether the session invoked the plugin, and which `state.md` is active. No event carries the assistant's text before a tool call.
- **Failure mode unchanged:** an error in the new events blocks nothing. If the data folder cannot be written, the verify check is off.

**Throwaway files (same release).** Session logs from 15 October to 14 November held 141 denials. Eighteen were probe, benchmark, or repro scripts, and 12 of the 17 in real projects were writes into Claude's scratch folder under the system temp folder. The 0.7.1 rule let only a shell redirect into temp through. Agents answered by putting probes under `.sdlc/changes/<slug>/probes/` (one repository now tracks 114 such files), by running scripts inline, or by stating the Fast lane.

- **Rule:** a file under the system temp folder, or a file Git ignores, is not project code. Every way of writing it passes before approval. A copy is checked on its destination only.
- Measured against the same logs: the temp rule lets 14 of the 19 throwaway writes through and none of the 87 denied writes to real code.

Rejected: letting any new file through that the plan does not name. It covers every probe, and also 7 of 71 denied writes to real code (new test files).

Rejected: a scratch folder with a fixed name. Git's ignore rules already say which files a project does not keep.

Rejected: denying on hook failure (`onFailure: "block"`), for the reasons in the 0.8.0 amendment.

Rejected for now: a guard on Codex. Codex 0.167 runs plugin hooks and accepts the same denial output, and a patch arrives as text from which paths can be read. But no event tells a hook that a skill was used, so the verify check and the "session uses the plugin" test cannot be decided, and Codex skips a plugin's hooks without notice until the user trusts them, after each plugin update, and under `codex exec`. A guard that covers only the approvals gate, decided from `state.md` on disk, is possible; it is a different design and needs its own behavior runs on Codex.

Known limits: see the changelog entry for 0.9.0.

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

## ADR-006: Close finished changes with a `closed` status and an archive folder (2026-10-31)

### Status

Accepted (2026-10-31).

### Context

A private review of two weeks of session logs found one project with 33 change folders under `.sdlc/changes/`, none closed, holding 311 tracked files. Agents had invented statuses (`done`, `complete`, `merged`, free text) and gate names (`delivery`, `spike`, `merged`) for work that ended without a release, because the contract had no status for a change that is finished but not released. Open folders also made resume ambiguous and fed the hook defects fixed in 0.6.2.

### Decision

Add `closed` to the `status` values in `artifact-contracts.md`. `closed` marks a finished change, or one the user calls abandoned; an agent closes only the current change. When a delivery finishes a change (released with no monitoring left, or merged with no later release planned), ship makes the last commit before the merge or release close it: `status: closed`, then `.sdlc/changes/<slug>/` moved to `.sdlc/archive/<slug>/`, or removed only where repository instructions explicitly say so. Closing inside that commit keeps it within the authorized delivery; a close after the merge would need a new commit and push to reach the integration branch. Without an authorized commit, ship reports the close as the next action. `status`, `lane`, `current_gate`, and approval `gate` take only the listed values; other decisions go below the header.

### Consequences

- The artifact contract gains one status value and one path, and restricts four fields to their listed values. Existing folders with other values stay where they are and fall outside the contract until closed; nothing migrates them. In `0.y.z` both kinds of change ship as a minor version (0.7.0).
- Newly finished changes leave `.sdlc/changes/`, so resume sees fewer stale folders.
- Until 0.7.1 the guard hook counted any `mv` or `rm` as a write outside `.sdlc/`, so it denied archiving a change that lacked the lane's gate approvals. Since 0.7.1 a move or removal whose every target is under `.sdlc/` passes.
- The guard hook reads only `.sdlc/changes/`. After archiving, a later write in the same session is checked against the lane stated in chat only.
- Compliance is instruction-only and therefore probabilistic (see ADR-003).

### Alternatives rejected

- **Reuse `released` as the terminal status.** It does not fit a change merged with no release step, or an abandoned one, which is where the invented statuses came from.
- **Delete finished folders by default.** It removes the in-repository record; Git history is harder to find than a folder. Removal stays available where repository instructions explicitly ask for it.
- **A single active-change pointer file.** The 0.6.2 hook already infers the active change from the session, and a shared pointer would fork across worktrees and branches the same way `state.md` did.
- **A status validator script.** An agent-run check holds no better than wording (ADR-004).

### Revisit when

Logs show agents still writing statuses or gate names outside the contract, or `.sdlc/changes/` still growing with finished work. Then add an enum check to `hooks/edit_guard.py` on writes to `state.md`.

## ADR-007: Run the Claude Code behavior checks with `claude plugin eval` (2026-11-06)

### Status

Accepted (2026-11-06).

### Context

The behavior suite ran by hand: a fresh headless session per case, scripted approval replies, then an independent transcript review. For 0.6.0 and 0.7.0 this took most of a working session per release. It gave one sample per case, and its recipe lived outside the repository. Five rules added in 0.7.0 had no case. Claude Code 2.1.319 ships `claude plugin eval`. It runs cases from `evals/`, repeats each case, adds a no-plugin baseline arm, enforces a cost ceiling, and scores runs with file, tool-call, and LLM graders.

### Decision

- Port the ten single-prompt cases to `evals/<case>/case.yaml`, and add five cases for the untested 0.7.0 rules: `reopen`, `scope-growth`, `guard-denial`, `close`, and `no-reply`.
- Each case's `scaffold.sh` writes its fixture with `python scripts/behavior_check.py seed . <case>`. `CASES` in that script stays the only fixture source, so the manual harness gets the five new cases too.
- Use deterministic graders for file and tool-call checks, and LLM graders only for judgments about the transcript or final report.
- Keep `feature` and `payment-build` on the manual harness. The case format has one prompt per case, and `context.history_file` only resumes a recorded transcript, so a case cannot reply to an approval stop.
- Keep `scripts/behavior_check.py` and the manual steps for Codex.

### Consequences

- One command runs 15 cases on Claude Code, 3 times each, with and without the plugin, under a cost ceiling.
- The eval refuses shell tools on native Windows because no sandbox backend exists there. The suite runs from Linux, macOS, or WSL2.
- No grader executes agent-written code. Code correctness is checked by content patterns and by the agent's own check runs.
- Runs use an isolated configuration: the user's global CLAUDE.md, plugins, and hooks do not load. Results are not directly comparable with the 0.7.0 manual runs, where the global CLAUDE.md stayed loaded.
- The without-plugin arm cannot pass graders that require a plugin skill call, so the delta measures the plugin's routing as well as its outcomes.
- A fixture change needs its `*-unchanged` patterns in `case.yaml` updated by hand.

### Alternatives rejected

- **Keep the manual harness only.** It costs a working session per release and gives one sample per case.
- **Pre-recorded transcripts (`history_file`) for the approval turns.** They test a recorded agent's earlier turn, not the plugin under test, and they force a single arm.
- **Run the eval on native Windows with a sandbox workaround.** Claude Code has no supported Windows sandbox for evals, and a workaround would not reproduce for other contributors.

### Revisit when

`claude plugin eval` supports scripted follow-up turns (then port `feature` and `payment-build`), command graders (then run the executable acceptance commands as graders), or a sandbox on native Windows.

## ADR-008: Route every delivery of a verified change through ship, and honor delegation requests (2026-11-07)

### Status

Accepted (2026-11-07).

### Context

The first full `claude plugin eval` run (ADR-007) on 0.7.1 found rule breaks in six cases, and the traces showed one cause each:

- `close`: every run that left the change open had committed straight from the router. The router's invariants required `ai-native-ship` only for a merge or release, although its routing list sent any authorized Git delivery there, so a plain commit could skip the close rule.
- `independent`: the router's "Keep small, tightly coupled work local" and "For Fast work, stay inline" won over the user's explicit request for parallel investigation.
- `model-override`: the agent treated controls read from a file as host state, or told the user to change host settings.
- `reopen`, `payment`, and `scope-growth`: the wording stated the rules without an order, or without naming every approval at the point where the report is written.

### Decision

- `ai-native-ship` handles every authorized commit, push, PR, merge into its target, or release of a verified Standard or Controlled change. Checkpoint commits during a build still follow `checkpoints.md` inside `ai-native-build`.
- A delivery finishes a verified change when no merge, release, or monitoring follows it, including a final commit to the delivery branch.
- A user's request for parallel or delegated work is an instruction to delegate when the host supports it, whatever the task size. Scopes that share files or mutable state stay sequential. Without such a request, small work stays local.
- A code change after `status: verified` overrides the stored `next_action`: set `status: building` before the first code edit or merge, then go through `ai-native-build`.
- A report that stops at a gate names each missing approval by gate and artifact, and any missing implementation or delivery authorization. Approvals recorded before a lane raise do not count for the raised lane.
- Model controls read from a supplied record are that record's claims and do not show that a described run took place; the next action comes from the review, not from changing host settings.

### Consequences

- A verified Standard or Controlled change that the user asks to commit now loads the ship skill, which adds one skill call to that commit.
- Small read-only tasks that ask for parallel work now cost worker handoffs. The user asked for that cost.
- These are compatible fixes of existing rules, so the release is a patch: `0.7.2`.

### Alternatives rejected

- **Check the close in the guard hook.** The hook sees file writes, not whether a commit finishes the delivery.
- **Drop delegation from the `independent` case.** The case follows an explicit user request; the router, not the case, was wrong.

### Revisit when

The next `claude plugin eval` run still fails any of these six cases. Then read those traces before changing the wording again.
