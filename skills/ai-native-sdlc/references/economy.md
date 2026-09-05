# Economy and simplicity

Apply these rules after understanding the relevant flow. Less reading is not a substitute for correct reading.

## Solution ladder

Stop at the first rung that meets acceptance and safety:

1. Remove speculative work. If the requested capability already exists or is not needed, do not build it.
2. Reuse an existing seam, helper, type, or repository pattern.
3. Use the standard library.
4. Use a native platform, browser, database, or framework feature.
5. Use an already-installed dependency.
6. Write the smallest local change.
7. Add a dependency, abstraction, mode, provider, configuration surface, or framework only when acceptance requires it.

For defects, trace callers and fix the shared root cause. A small patch at the wrong layer is not simple.

Prefer deletion over addition and boring code over clever code. Do not create single-use interfaces, one-product factories, future scaffolding, configurable constants, or wrappers that only rename an API.

Never simplify away trust-boundary validation, security, privacy, accessibility, required compatibility, or error handling that prevents data loss. Record a deliberate ceiling only when a real tradeoff remains, with the condition that would justify an upgrade.

## Context budget

- State the question each read must answer. Search paths and symbols first, then read the smallest complete span that answers it.
- Trace required callers and boundaries, but do not load unrelated directories, every reference, full logs, or whole test suites into context.
- Do not reread unchanged material. Put durable decisions and the next action in `state.md`, not a conversation transcript.
- Keep tool output to the decisive failure, counts, and affected locations when full output is not required for correctness.
- Stop exploration when the next decision is supported. Stop implementation when acceptance passes.

## Delegation

- Follow host, repository, and user instructions first. Otherwise keep small, tightly coupled work local. Delegate bounded independent work, substantial noisy investigation, or required independent review when the benefit justifies handoff and integration effort. Agent availability alone is not a reason.
- Keep one integration owner responsible for the outcome, decisions, current state, and user communication. Assign distinct write scopes and dependencies; shared files or mutable state stay sequential.
- Send objective, acceptance criteria, applicable instructions, relevant paths and revision/diff (including uncommitted changes), allowed tools/writes, dependencies, proof command, and stopping condition. Use host permission controls where available; a prompt is not a sandbox. Workers escalate scope changes and do not delegate further by default.
- Choose context using actual host capabilities: fresh for self-contained work or independent review; fork when substantial shared history is needed; resume only a supported worker whose task and evidence remain relevant. Forking can reuse cached context. A separate agent is not automatically fresh, unbiased, or cheaper. Change models only when permitted and justified by acceptance quality and total cost.
- Return conclusions, exact locations or changed files, inspectable command results and exit status, limitations, and blockers. Keep raw logs outside the main thread with evidence pointers; do not request a reasoning transcript.
- While a worker runs, do non-overlapping work or wait. Do not repeat its investigation merely to stay busy; inspecting decisive evidence for integration is still required. Stop or re-scope obsolete workers. Check late results against current requirements and code before integrating, then verify the integrated change fresh.

## Output budget

- Lead with the result. Use one short sentence per fact and stable technical terms.
- Remove pleasantries, repeated restatement, narration, speculative tours, and conclusions already implied by evidence.
- Preserve exact code, commands, file paths, errors, names, versions, dates, numbers, units, and words such as `not`, `never`, `only`, and `except`.
- Do not invent abbreviations or damage grammar for cosmetic brevity.
- Expand when compression could obscure a security warning, irreversible action, ordered procedure, architectural disagreement, or requested explanation.

## Measurement

Shorter output or a cleaner main context does not automatically reduce total cost. Claim savings only from repeated paired runs on the same baseline and host/model/settings, with independent quality checks and equal verification. Count parent and worker usage, retries, and integration work; distinguish cached usage, monetary cost, and elapsed time where measurable. Missing usage means no savings claim. Keep a cost optimization only when total cost falls without weaker results.
