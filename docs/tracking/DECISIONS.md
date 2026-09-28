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
