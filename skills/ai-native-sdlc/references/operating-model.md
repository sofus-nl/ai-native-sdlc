# Operating model

## Choose one lane

Use the highest applicable risk signal. Do not average risks downward.

### Fast

Use for a small, reversible, well-specified edit with no security, privacy, money, migration, production, or destructive effect.

- No lifecycle files are required.
- Inspect the real path, state a short plan, make the smallest change, review the diff, and run the narrowest meaningful proof.
- Escalate to Standard if investigation reveals unclear behavior, more than one independently failing component, or a wider blast radius.

### Standard

Use for ordinary bugs and bounded features.

- Preserve accepted intent and acceptance criteria in `.sdlc/changes/<slug>/spec.md`; use `intent.md` when the request is materially ambiguous.
- Create `plan.md` and `state.md` before implementation.
- Require focused tests, diff review, and fresh verification.
- Use isolated work and independent agents when they reduce collision or confirmation bias; they are not ceremony requirements.

### Controlled

Use when work touches authentication, authorization, secrets, privacy, payments, destructive data changes, production infrastructure, regulated behavior, public contracts, or multiple services.

- Require accepted `intent.md`, `spec.md`, `plan.md`, named human gates, rollback or recovery proof, isolated work, and independent review.
- Separate the author, reviewer, and approver roles when the host supports it.
- Production stops at an explicit human authorization even if every automated check is green.

## Gates

1. **Intent:** Is the desired outcome and boundary correct?
2. **Design:** Do requirements, constraints, and acceptance checks resolve the intent?
3. **Plan:** Are exact change points, dependency order, risks, and proof known?
4. **Build:** Does each task produce a bounded, testable result without scope drift?
5. **Review:** Does the diff match intent and plan, and is it technically safe?
6. **Verify:** Do fresh commands or observations prove the claims?
7. **Release:** Are approvals, rollback, and post-release checks ready?
8. **Operate:** Are deterministic signals inside their control bands, and do incidents feed the right layer?

At a failed gate, repair that layer and repeat downstream gates. Do not patch evidence to make a gate green.
