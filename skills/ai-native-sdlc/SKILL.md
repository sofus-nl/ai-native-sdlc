---
name: ai-native-sdlc
description: Route software work through a risk-sized AI-native lifecycle from intent to operations. Use for end-to-end features, fixes, delivery workflows, resuming a change with existing SDLC artifacts, and read-only reviews of model selection, model qualification claims, or model cost. Use whenever the user asks to use ai-native-sdlc.
---

# AI-Native SDLC

Turn software work into a closed evidence loop without forcing enterprise ceremony onto small changes.

When a leaf skill opened this file, use only its lane, invariants, and Output rules. Do not route or invoke another copy of that leaf.

## Start

1. Read repository instructions, current status, relevant code, tests, and existing `.sdlc/` artifacts.
2. Restate the requested outcome, explicit boundaries, and assumptions. Do not widen authorization.
3. Choose the lane. Fast means small, reversible, clear, and no security, privacy, money, migration, production, destructive, or cross-service effect. Controlled means any of those risks. Standard covers the middle, including bounded features, ordinary bugs, and any request that asks for a plan or specification. A risk signal you cannot rule out after reading the relevant code counts as present. Size never lowers the lane. State the lane in a message before the first file change, as `Lane: Fast`, `Lane: Standard`, or `Lane: Controlled`. Never lower the current change's lane to clear a guard denial; get the missing approvals or report the denial. When scope grows mid-change, for example when the change starts to handle untrusted input (a security risk signal), run this lane test again and raise the lane if a risk signal now applies; approvals recorded before the raise do not count for the raised lane, so obtain each of its approvals on the revised artifacts. Standard and Controlled work edit no code until `state.md` records a `plan` approval (Controlled also needs `intent` and `design` approvals); a small or fully specified task, a request that already authorizes implementation, or a general instruction to avoid extra files does not waive this. Read [operating-model.md](references/operating-model.md) only for Standard, Controlled, or unclear classification.
4. Use the first sufficient option: skip speculative work, reuse existing code, use the standard library, use a native feature, use an installed dependency, then write minimum new code. Keep small, tightly coupled work local unless applicable instructions require delegation. A user's request for parallel or delegated work is such an instruction when the host supports it, whatever the task size; scopes that share files or mutable state still run sequentially. Read [economy.md](references/economy.md) for Standard or Controlled work, complex context, substantial output, or before delegating.
5. If `.sdlc/changes/*/state.md` identifies this work, resume its `next_action`, unless the request changes code after `status: verified` (see Invariants); do not restart the lifecycle. For model selection, model qualification claims, or cost comparisons, read [model-selection.md](references/model-selection.md) before answering, including read-only and Fast work.
6. For Fast work, stay inline apart from delegation the request asks for: state the short plan, make the smallest authorized edit, inspect the diff, run focused proof, and report fresh evidence. Use `ai-native-debug` first only when the cause is unknown; when the request asks for parallel or delegated work, dispatch one worker per scope and have each apply `ai-native-debug` to it. Do not create lifecycle files.
7. For Standard or Controlled work, invoke only the next matching skill through the host's skill mechanism; never do a leaf skill's work from this router:
   - unclear outcome, new product behavior, no `spec.md` yet, or Controlled work without an approved `intent.md` -> `ai-native-shape`; a plan-only request still gets draft `spec.md` and `plan.md`, with nothing marked accepted and the approvals still needed listed, including the Controlled approval after checkpoint 1
   - accepted outcome with `spec.md` needing implementation design -> `ai-native-plan`
   - accepted plan -> `ai-native-build`
   - defect or failed check with unknown cause -> `ai-native-debug`
   - completed diff needing assessment -> `ai-native-review`
   - claim needing proof -> `ai-native-verify`
   - authorized Git delivery or verified change needing release -> `ai-native-ship`
   - production signal, incident, or learning -> `ai-native-operate`

## Invariants

- The user owns judgment gates and irreversible actions. An agent may prepare evidence but never self-approve. Authorization to implement does not approve intent, plan, or checkpoints: Controlled gates need an in-session human decision on the named artifact, given after that artifact exists. Before recording any approval, run a clock command (for example `date -u +%Y-%m-%dT%H:%M:%SZ`) and use its output as `at`. No answer is not consent: a question that times out or goes unanswered blocks the gated step. A timeout never authorizes a commit, push, merge, tag, publish, or deploy, even one you announced as the default. Ask again before acting differently from what you announced.
- Trace every artifact to the requested outcome. Tests passing does not prove the right thing was built.
- Keep one source of truth per artifact. Cross-link external tickets or documents instead of silently duplicating authority.
- Fix the earliest incorrect layer: intent, specification, plan, code, test, release, or control band.
- Stop at the first simple solution that satisfies the accepted outcome and safety constraints.
- Use deterministic checks for deterministic rules. Agent review supplements tests, policy enforcement, and access controls.
- Update `state.md` only when a durable artifact exists. Record facts, decisions, evidence, deviations, and the next action, not chat history.
- Never commit, push, open a PR, deploy, roll back, message people, or modify external systems without authorization already present in the request.
- Completion claims require fresh evidence. Standard and Controlled work invoke `ai-native-review` on the full diff, then `ai-native-verify`, before claiming a code change complete, and `ai-native-ship` for any authorized commit, push, PR, merge into its target, or release of a verified change. Dispatching a reviewer or verifier agent instead of invoking the skill does not count. Fast work may verify inline.
- A code change after `status: verified`, including a merge of another branch into the change, reopens the change. Before the first code edit or the merge, set `status: building` and `next_action` to the affected checkpoint, then invoke `ai-native-build`; it routes the delta through `ai-native-review` and `ai-native-verify` before any completion claim, merge, or release. For a merge, the delta is every incoming change not already reviewed, plus conflict resolutions.
- Finish every in-scope part of the request. Leave no placeholders, stubs, `TODO`s, elided code such as `// rest unchanged`, or silently deferred remainder. Minimal means the least code per part, not fewer parts. Report a part you cannot finish as unmet with its reason, never as done.

For artifact shapes, read [artifact-contracts.md](references/artifact-contracts.md) only when creating or updating lifecycle files.

For version selection or release compatibility, read [semver.md](references/semver.md). Apply it to the software being delivered, not just this plugin; preserve explicit repository policy and release authorization.

For authorized Git checkpoints, including Fast work, apply [checkpoints.md](references/checkpoints.md); deliver a verified Standard or Controlled change through `ai-native-ship`. Commit, branch push, merge, and release have distinct evidence and authorization boundaries.

## Output

Lead with the result. State lane, evidence, risk, next action, and blocker once. Preserve exact code, commands, paths, errors, numbers, and negation. Mark each requested part met or unmet. When work stops at a gate, name each approval the lane still needs, by gate and artifact: Standard needs `plan` on `plan.md`, plus `intent` on `intent.md` when the request is materially ambiguous; Controlled needs `intent` on `intent.md`, `design` on `spec.md`, `plan` on `plan.md`, and `checkpoint` after checkpoint 1. Also name any implementation, commit, push, merge, or release authorization the request lacks. Re-measure every number you report; label any other number `not measured`.
