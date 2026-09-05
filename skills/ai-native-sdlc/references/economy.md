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
- Give workers only the task, authoritative acceptance IDs, relevant paths or artifact excerpts, allowed scope, and proof command.
- Ask workers for conclusions, locations, decisive evidence, and uncertainty. Do not ask for their full reasoning or raw logs.
- Keep tool output to the decisive failure, counts, and affected locations when full output is not required for correctness.
- Stop exploration when the next decision is supported. Stop implementation when acceptance passes.

## Output budget

- Lead with the result. Use one short sentence per fact and stable technical terms.
- Remove pleasantries, repeated restatement, narration, speculative tours, and conclusions already implied by evidence.
- Preserve exact code, commands, file paths, errors, names, versions, dates, numbers, units, and words such as `not`, `never`, `only`, and `except`.
- Do not invent abbreviations or damage grammar for cosmetic brevity.
- Expand when compression could obscure a security warning, irreversible action, ordered procedure, architectural disagreement, or requested explanation.

## Measurement

Shorter output does not automatically reduce input or reasoning tokens. Instructions also cost tokens. Claim savings only from paired runs of the same task using provider totals and an independent quality check. Keep an optimization only when total cost falls without weaker results.
