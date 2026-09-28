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
