# Model selection: second-pass review

Date: 2026-09-05. Target: the model-selection research proposal after v0.4.0. Status: revised proposal, not an implemented router or a qualified model catalog. No verification gate, model default, or quality threshold is changed by this review.

## 1. Load-bearing claims

1. The proposed Haiku/Luna, Sonnet/Terra, Opus/Sol, Fable/Astra task bands are a useful basis for cheapest-qualified-model selection.
2. Verification and escalation can preserve quality while reducing cost.
3. A shared skill can reliably apply the intended model selection across hosts.

## 2. Strongest objections and decisions

### Model bands: revised to experiment candidates

Objection: prices and vendor positioning do not establish task-level capability, cross-provider equivalence, or a monotonic quality ranking. No evaluation of these eight current models was performed for this plugin. Task labels such as debugging span very different levels of difficulty.

Decision: keep the eight names only as candidates for qualification. Do not turn the previous four-row table into automatic defaults. Qualification attaches to exact model/version, reasoning effort, host/tools, context mode, and task class. Use the existing user-approved baseline when no cheaper route has evidence. If no baseline exists, disclose that selection is provisional rather than asserting qualification.

Price audit: the previously quoted standard uncached API rates remain supported by the provider pages. They are not subscription charges. A fixed price order still fails on cached work: Fable 5.1 lists cache reads at $0.25 per million tokens versus Opus 5 at $0.50, despite higher Fable uncached/output rates. Compare expected complete request costs, including cache creation, outputs, retries, and service tier; do not assume a cache created for one model transfers to another. [Anthropic pricing](https://claude.com/pricing), [OpenAI pricing](https://developers.openai.com/api/docs/pricing)

### Quality preservation: revised to an explicit evidence requirement

Objection: a model can produce plausible wrong answers that pass incomplete checks, so escalation never triggers. Strong-model review also has false negatives. Equal aggregate scores can conceal losses on tasks the baseline solved, offset by wins elsewhere.

HyDRA's abstract describes matched quality, but Table 2 reports conservative routing at 74.0% resolution versus Sonnet 4.6 at 74.2% on 500 tasks: `0.740 * 500 = 370` versus `0.742 * 500 = 371` solved, alongside 54.1% cost savings. That is near aggregate parity, not exact parity; a nonsignificant difference is not proof of equivalence. Its five-model pool does not qualify our eight proposed families. SWE-Router uses early trajectories for routing; its Bayes-optimal result is not a guarantee for a learned selector or an individual task. Both cited source records were checked without finding a withdrawal notice. [HyDRA Table 2, v2](https://arxiv.org/html/2605.17106v2#S5.T2), [SWE-Router](https://arxiv.org/html/2607.00053v1)

Computation: for an illustrative independent Bernoulli sample with zero observed misses, the exact one-sided 95% upper bound on miss probability is `1 - 0.05^(1/n)`. At n=8 it is 31.23%; at n=100 it is 2.95%. Our eight heterogeneous smoke fixtures do not satisfy a representative independent sample assumption and did not compare model variants; they support neither bound as a reliability estimate. The calculation shows why a clean smoke suite is not proof of no quality loss.

Decision: retain unchanged integrated verification and required review. Evaluate paired tasks and inspect baseline-success/router-failure cases separately from average score. No quality-loss tolerance is silently introduced. Claims must say what was observed, on which tasks, with what uncertainty. If there is no supporting qualification data, do not automatically downgrade quality-critical work.

Cost counterexample (illustrative dollars, not measured usage): a cheap attempt costs 0.10, incremental screening costs 0.15, and a fallback including its normal verification costs 1.00. With fallback probability 0.80, expected cost is `0.10 + 0.15 + 0.80 * 1.00 = 1.05`, above direct baseline cost 1.00. Here routing saves only if the fallback probability is below 0.75, before any other overhead. This is an example, not a production routing threshold. Failure detection still must be evaluated independently.

### Host enforcement: defended with a narrower contract

Objection: a model request is not a receipt. Host settings can substitute models, forks may inherit settings, and some surfaces do not expose reliable model identity or overrides. A shared skill cannot create cross-provider access.

Current Claude documentation supports model aliases and per-invocation selection but describes allowlist substitution. This session's Codex tool schema exposes model/effort overrides for permitted fresh or partial forks, while full-history forks inherit the parent. Those observations do not establish identical support in every Codex/ChatGPT surface. [Claude controls](https://code.claude.com/docs/en/sub-agents#choose-a-model)

Decision: separate selection policy, host execution, and evidence. Record requested and resolved model/settings where the host supplies them. A tool accepting a requested model without reporting its resolution establishes a request, not verified execution identity. If resolution or cost is unobservable, report it as unverified; do not claim cheapest execution. Retain the configured baseline if override is unavailable. Report hard requirements that the host cannot satisfy rather than pretending compliance. Switching providers requires an already authorized, configured runtime and data-access scope.

## 3. Major-claim audit

| Claim | Initial tag | Disposition |
| --- | --- | --- |
| Current price snapshot | SOLID | Rechecked, retain only with API/cache/tier/date scope |
| Four task bands identify qualified models | CONVENTIONAL | Rewrite as experiment candidates; no equivalence or automatic downgrade |
| Routing can reduce aggregate benchmark cost | SOLID | Retain within cited model pools and benchmarks |
| Equal aggregate score means no quality sacrifice | CONVENTIONAL | Replace with paired outcome analysis and uncertainty disclosure |
| Verification and escalation catch every weak result | CONVENTIONAL | Cut guarantee; account for missed errors and preserve gates |
| Inspecting early work can inform selection | SOLID | Retain as supported research direction, not a proven plugin heuristic |
| Every failure warrants a stronger model | CONVENTIONAL | Reject: first distinguish task difficulty from missing permissions, tools, or a broken environment |
| Shared instructions can enforce model identity | CONVENTIONAL | Replace with host controls plus observable identity; unknown remains unknown |
| Cheapest token rate minimizes total job cost | CONVENTIONAL | Replace with full-attempt expected cost and actual billing basis |
| Runtime instructions alone cannot guarantee quality | SOLID | Retain |

## 4. Preserve these strengths

- No per-task guarantee of cheapest successful execution.
- No global fixed model override or automatic main-thread model change.
- No change to integrated-state verification, independent review requirements, or authorization.
- No automatic cross-provider execution or new orchestration service.
- Measure failed attempts and integration work as well as successful calls.
- Keep discovery lightweight and detailed selection guidance on demand.

## 5. Revised proposal in full

Define the objective as minimizing observed or estimated complete task cost among available, authorized, qualified configurations while preserving the user's existing acceptance and review requirements. Explicitly identify whether cost means metered API spend, subscription allowance consumption, or latency. When those cannot be mapped reliably, do not label a monetary winner.

Use a small on-demand model-selection reference and a documented qualification record. The record needs task class, concrete model/version and effort, host/tools/context, evidence, and measured cost basis; it need not be a new runtime database. All eight named families start as candidates, not interchangeable tiers. Existing baselines remain active until evidence supports a cheaper route. Model or host changes require reassessing the affected qualification.

For an eligible task, inspect scope, uncertainty, dependencies, tool needs, and verification coverage. Select a qualified configuration through supported native controls; retain the main-thread model unless its change is separately supported and authorized. Do not spawn a worker solely because its price per token is lower when finishing locally is cheaper overall.

Record requested versus observed model/effort and context mode where available. Unknown resolution is not proof of failure, but it prevents a verified model/cost claim. Unsupported overrides retain the configured baseline; unmet mandatory model constraints are reported. No silent substitute is labeled as the requested model.

Use short exploration when it can resolve routing uncertainty economically. Escalate for observed capability shortfalls or newly discovered complexity, not automatically for missing credentials, unavailable tools, or environment failures. Preserve the authoritative task, evidence, and current diff when handing off. Avoid an unbounded cycle through model names. Required proof and integration ownership remain unchanged.

Before enabling cheaper defaults, compare exact configurations on held-out representative tasks using repeated runs and the same acceptance, tools, and final verification. Report paired regressions, per-task-class results, critical failures, aggregate cost, retries, and uncertainty. Choose evaluation size from the required assurance, not a fixed small sample. The existing eight cases test workflow behavior; they do not qualify models.

Add behavior cases for unavailable overrides, observable substitution, undetected-by-basic-tests defects, capability-based escalation, and cheaper-looking routes whose retries erase savings. These validate policy mechanics; live host readback and representative model evaluation validate the operational claims. Do not promise a quality-preserving automatic router from Markdown alone.

## Second-pass corrections / telemetry

- Corrected the implied qualification of a vendor-family table: candidates now remain unqualified until task-specific evidence exists. Future recommendations must distinguish vendor positioning, benchmark evidence, and local qualification.
- Corrected the HyDRA headline against its actual table: 370 versus 371 solved is not exact parity. Future routing research must check underlying tables and paired outcomes, not repeat abstract parity claims; statistical nonsignificance does not establish equivalence. Require paired losses and uncertainty; do not call eight smoke passes evidence of model reliability.
- Made hidden verification failures explicit: stronger review is not an oracle, and no new quality tolerance or verification exception is applied.
- Recomputed an escalation-cost counterexample and a zero-event confidence bound; both are illustrative, not calibrated thresholds.
- Narrowed model enforcement to requested versus observed identity. This audit requested Terra/medium for bounded source checking; acceptance of the spawn request alone is not a measured quality or billing result.
- Prior deliverable was chat-only. This file is the full revised artifact and correction record; the changelog records it. No runtime skill, installed configuration, or public repository state was changed by this review.

External verification: an independent domain owner must judge whether apparent baseline/router parity on representative private tasks misses unacceptable defects; this review has neither that workload nor authority to relax its quality requirements.
