# Sub-agent optimization: second-pass review

Date: 2026-09-05. Target: the research recommendation following commit aa17d9d, not an implemented skill change. Status: revised proposal; no runtime instructions or verification gates changed.

Implementation follow-up: v0.4.0 applies the delegation/context/handoff guidance and extends the behavior checks after user authorization. The review below is the historical correction record. Verification gates remain unchanged; performance benefits remain unmeasured.

## 1. Three load-bearing claims

1. Selective delegation is a better default for this plugin than mandatory delegation.
2. Fresh workers with compact returns improve context management.
3. Reusing worker execution evidence can reduce redundant verification without weakening correctness.

## 2. Strongest objections and decisions

### Delegation: defended, with narrower evidence transfer

Objection: results from research and game planning cannot establish that a particular policy improves this coding plugin. The same study includes coding evaluations, so describing the whole study as non-coding would also be inaccurate.

Source audit: Scaling Agent Systems v3 reports 260 configurations. Its roughly 39-70% relative degradation is on PlanCraft, a game-planning benchmark. It also includes SWE-bench Verified and Terminal-Bench, but only 20 instances each, with wide uncertainty. No withdrawal notice was found on the arXiv record. These findings establish task dependence, not this plugin's optimal policy. [Paper v3](https://arxiv.org/html/2512.08296v3)

Decision: retain selective delegation as a design proposal because independent work can run concurrently while dependent work incurs handoff costs. Do not claim measured coding gains. Repository/user requirements still take precedence over plugin defaults.

### Fresh context: revised

Objection: copying context can reuse a prompt cache; rebuilding it can cost more. Separate context does not necessarily mean a worker lacks the parent's history or assumptions. Resume is not universally supported.

Current Claude documentation distinguishes non-fork workers from conversation forks, which inherit history and can reuse the parent's prompt cache. Some built-in workers cannot be resumed. [Host documentation](https://code.claude.com/docs/en/sub-agents#fork-the-current-conversation)

Decision: use minimal fresh context for independent review or self-contained investigation; use a fork when substantial shared context is necessary and the host supports it. Resume only where supported and when the task and evidence remain applicable. Check actual tool semantics. Do not equate a new agent with independent judgment or lower cost.

### Verification reuse: revised; gate change deferred

Objection: passing tests in a worker checkout do not prove the integrated tree passes. Claimed exit status is not trustworthy execution provenance. Reusing it indiscriminately weakens the current verification rule.

Local source audit: build explicitly requires inspecting the diff and running the relevant check; verify requires fresh checks in the current environment. These are intentional gates, not proven waste. No traces were measured to establish duplicate-check cost.

Decision: retain final verification of the integrated change. Consider removing only redundant intermediate runs after a separate evidence policy defines exact tree/diff identity (including uncommitted changes), command, environment, result provenance, and invalidation. Do not amend build/verify gates in this review.

## 3. Major-claim audit

| Claim | Initial tag | Disposition |
| --- | --- | --- |
| Delegation effectiveness depends on task structure | SOLID | Source-supported; retain |
| Our proposed policy will improve coding cost/quality | CONVENTIONAL | Rewrite as a hypothesis requiring paired runs |
| Isolating verbose exploration can keep it out of the main thread | SOLID | Retain; not a total-token savings claim |
| Fresh workers are always the cheaper/better context choice | CONVENTIONAL | Replace with host-aware fresh/fork/resume selection |
| Clear ownership and evidence requirements address known failure categories | SOLID | Retain as design rationale, not proven mitigation effectiveness |
| One reviewer is the optimal reviewer count | CONVENTIONAL | Rewrite as a minimal starting heuristic; distinct risk and required independence can justify more |
| Repeated checks are unnecessary because a worker already passed them | CONVENTIONAL | Cut; preserve integrated-state verification |
| Cheaper models should handle simple tasks | CONVENTIONAL | Make conditional on host support and observed acceptance/rework cost |
| Total parent-plus-worker cost and quality must be measured | SOLID | Retain; include retries and integration work |
| Always using sub-agents necessarily conflicts with optimization | CONVENTIONAL | Rewrite: it can impose avoidable overhead, but local policy and task goals govern |

The failure-taxonomy paper reports 1,600+ traces across seven frameworks; taxonomy construction involved 150 expert-guided traces. Neither its arXiv v3 record nor the scaling paper record showed withdrawal. It identifies failures, not experimental proof that our brief fixes them. [Failure taxonomy v3](https://arxiv.org/abs/2503.13657v3)

Anthropic's reported 15x token use is relative to chats, not single agents. Its separate 4x figure for agents does not establish a controlled 15/4 cost ratio for our workload. The internal research evaluation is not our coding evaluation. [Engineering report](https://www.anthropic.com/engineering/multi-agent-research-system)

## 4. Anti-churn: retain these strengths

- One integration owner and explicit write ownership.
- Parallelize independent work; serialize shared files and mutable state.
- Compact results with inspectable evidence; no raw-log dumping.
- Preserve authorization and independent review requirements.
- Keep quality, token cost, and elapsed time distinct.
- Reuse the existing shared economy reference; do not introduce an orchestration framework.

## 5. Revised proposal in full

Subject to repository and user instructions, keep small, tightly coupled tasks in the main thread. Delegate a bounded independent task, substantial noisy investigation, or required independent review when its benefit justifies handoff and integration work. The main agent retains outcome, decisions, integration, and communication; it may delegate critical-path work when that is the best execution choice.

Before dispatch, specify objective, acceptance criteria, relevant files and current tree/diff identity, applicable instructions, allowed tools/writes, dependencies, proof, and stopping condition. Use available host controls for permissions; a prose scope statement is not a sandbox. Workers return conclusions, exact locations or changed files, inspectable execution evidence, limitations, and blockers. Do not spawn nested workers or expand scope by default.

Choose fresh, forked, or resumed context deliberately, according to the actual host. Independent reviewers need the specification, boundaries, and diff, but do not need the author's persuasive account of why the implementation is correct. Fresh context does not guarantee unbiased review. Model selection remains conditional on host support and demonstrated result quality, not hardcoded model names.

While a worker runs, the parent does useful non-overlapping work or waits for its result. It does not repeat the assigned investigation merely to stay busy. Re-reading decisive evidence for integration or review is legitimate, not automatically duplication. Stop or re-scope obsolete workers when requirements change; never merge a late result without checking it against current state.

Use one reviewer covering outcome, engineering, and simplicity as a starting heuristic, with additional independent review where risk or policy requires it. Preserve human approval boundaries and final verification on the integrated change. Any policy for reusing intermediate execution evidence is a separate proposed gate change.

Implement first in the existing economy reference and concise plan/build/review handoffs; do not change verification semantics as part of that patch. Extend behavior cases for a tiny local task, independent investigations, shared-state serialization, and a stale worker result after integration. Tests must permit higher-priority policies that require delegation rather than scoring instruction compliance as failure.

Compare current versus revised instructions on identical fixture baselines with matched host/model/settings. Record repeated runs, failures, retries, total parent-plus-worker tokens, cached/uncached usage and monetary cost where available, elapsed time, and integration rework. Grade acceptance independently without revealing the variant. Keep evidence collection and final verification equal between variants. The existing five smoke cases are not a savings or reliability benchmark; missing usage data means no savings claim.

## Second-pass corrections / telemetry

- Scope-transfer error: qualified PlanCraft percentages and acknowledged small coding samples. Future research updates must name benchmark, version, baseline, and transfer limit before turning a finding into a skill rule.
- Host-semantics omission: added fork caching and resume capability checks. Future context recommendations must distinguish separate output history from input isolation.
- Gate weakening risk: withdrew the bundled verification relaxation. Fresh integrated-state proof and approvals remain unchanged; any exception stays a proposal until explicitly authorized.
- Unmeasured efficiency claim: replaced implied benefit with a paired-evaluation requirement, including failure/retry cost and equal verification.
- Prior deliverable was chat-only. This file is the full revised artifact and correction record. Changelog records the review. No plugin instruction, standing user policy, or public repository state was modified by this review.

External verification: independently judge the revised policy's usefulness on representative private projects; this review has no representative workload or measured provider usage proving the benefit.
