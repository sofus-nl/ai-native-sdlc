# AI-Native SDLC

Build less. Prove it. Ship safely.

A lightweight software delivery plugin for **Claude Code and OpenAI Codex**, with one shared set of nine skills. It connects intent, planning, implementation, review, verification, release, and operations while sizing the process to the risk of the change.

The plugin adapts workflow ideas from Anthropic's AI-native SDLC playbook, Superpowers, GSD, BMAD, G-STACK, Ponytail, and Caveman. It uses original instructions; those frameworks are not dependencies or bundled runtimes.

## Install

Use a current Claude Code or Codex release with plugin support. The plugin itself needs no API keys, package installation, MCP servers, or background services. Your host still needs its normal account and tools.

### Claude Code

Run in a terminal:

```sh
claude plugin marketplace add sofus-nl/ai-native-sdlc
claude plugin install ai-native-sdlc@ai-native-sdlc-marketplace --scope user
```

Start a new Claude Code session, or run `/reload-plugins` in an existing one. Then:

```text
/ai-native-sdlc:ai-native-sdlc Add CSV export to the existing reports page. Reuse the current data and UI components.
```

### OpenAI Codex

Run in a terminal:

```sh
codex plugin marketplace add sofus-nl/ai-native-sdlc --ref main
codex plugin add ai-native-sdlc@ai-native-sdlc-marketplace
```

Start a new Codex task so skill discovery reloads. Select `ai-native-sdlc` from the available skills, or ask:

```text
Use the ai-native-sdlc plugin to add CSV export to the existing reports page. Reuse the current data and UI components.
```

### ChatGPT workspace

Where workspace plugin import is available, a workspace admin can open **Workspace settings > Plugins > Add > Import marketplace** and enter:

- Source: `https://github.com/sofus-nl/ai-native-sdlc`
- Path: leave empty
- Branch: `main`

Import the marketplace, then review the plugin's installation policy and workspace access. OpenAI accepts this repository's Claude-compatible marketplace format. See [GitHub marketplace import and sync](https://help.openai.com/en/articles/20001504-importing-and-syncing-plugin-marketplaces-from-github). Availability depends on your account, role, and product surface; workspace import has not been tested for this release.

Publishing this repository does not automatically list the plugin in a public directory. Uploading a ZIP into a regular conversation does not install it. Other agents may be able to load the `skills/` files, but their compatibility is not verified here.

See the official [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) and [OpenAI plugin packaging documentation](https://developers.openai.com/plugins/build/plugins). Use `codex plugin --help` for commands supported by your installed version.

## Use it

Start with the router, `ai-native-sdlc`, when you want it to choose the next step. You can also request a specific skill:

| Skill | Purpose |
| --- | --- |
| `ai-native-sdlc` | Choose the risk lane and next action; resume existing work |
| `ai-native-shape` | Clarify the outcome, boundaries, and acceptance criteria |
| `ai-native-plan` | Plan concrete changes, dependencies, risks, and proof |
| `ai-native-build` | Implement the smallest change that meets the plan |
| `ai-native-debug` | Trace failures to their cause before changing code |
| `ai-native-review` | Check correctness, intent, risk, and unnecessary complexity |
| `ai-native-verify` | Gather fresh evidence for completion claims |
| `ai-native-ship` | Prepare an authorized release and its verification |
| `ai-native-operate` | Turn operational signals and incidents into follow-up work |

In Claude Code, prefix a skill with `/ai-native-sdlc:`, for example `/ai-native-sdlc:ai-native-review`. In Codex, select or name the skill.

Useful requests:

```text
Use ai-native-debug to investigate the failing checkout test. Diagnose first.
Use ai-native-plan to plan this feature using existing components and no new dependencies unless required.
Use ai-native-review to review this diff against the acceptance criteria and identify unnecessary abstractions.
Use ai-native-verify to check the completed change and report what remains unverified.
Use ai-native-sdlc to resume the change recorded in .sdlc/changes/csv-export/state.md.
```

## How much process?

| Lane | When | Artifacts and checks |
| --- | --- | --- |
| Fast | Small, clear, reversible changes without elevated risk | Inline plan, minimal edit, focused verification; no lifecycle files |
| Standard | Bounded features and ordinary bugs | Specification, plan, state, review, and fresh verification |
| Controlled | Security, privacy, payments, migrations, production, destructive changes, or cross-service effects | Explicit intent and human gates, independent review, and recovery evidence |

Standard and Controlled work keep durable artifacts under `.sdlc/changes/<slug>/`. Existing state identifies the next action, so work can resume without replaying the whole conversation. Only create the artifacts the chosen lane needs.

The agent follows repository instructions and the user's authorization. The skills do not grant permission to commit, publish, deploy, or change external systems. They are instructions, not a sandbox or an enforced policy engine.

## Simplicity and token use

The shared economy policy favors existing code, standard libraries, native capabilities, and the smallest sufficient change. It discourages speculative abstractions, duplicate artifacts, broad context loading, repeated reads, and continued implementation after acceptance passes.

Reference documents load only when needed. Concise output must preserve exact commands, identifiers, evidence, and important qualifications. No percentage token savings is claimed: savings require paired task runs measuring provider totals and result quality.

Delegation is conditional on task independence, context needs, and review requirements, subject to host and repository instructions. Workers receive bounded scopes and return compact evidence; one owner integrates results and verifies the current change. Fresh, forked, or resumed context depends on host capabilities. See the [reviewed rationale](docs/research/subagent-optimization-second-pass.md).

Model selection uses an [on-demand policy](skills/ai-native-sdlc/references/model-selection.md): retain the configured baseline until task-specific evidence supports a cheaper model/effort configuration. The eight named model families are candidates, not preset tiers. Native host controls govern execution; unsupported overrides and unverified model identity are reported. Complete-task cost includes retries and verification. No automatic router, cross-provider access, or guarantee of equal quality is bundled. See the [reviewed rationale](docs/research/model-routing-second-pass.md).

## Troubleshooting

- **Skills are missing:** verify installation with `claude plugin list --json` or `codex plugin list`, then start a fresh session/task.
- **You installed an earlier local version:** it may coexist under `ai-native-sdlc@personal` in Codex. Keep one active copy if duplicate skills appear.
- **Too much ceremony:** state the actual scope and ask the router to explain its lane choice. A genuinely low-risk edit should use Fast.
- **Other workflow plugins compete:** invoke this plugin explicitly and disable overlapping plugins if their instructions conflict.

## Development and contributions

The repository root is the plugin root. `.claude-plugin/` supplies the Claude manifest and marketplace; `.codex-plugin/` supplies Codex metadata; both hosts use the same physical `skills/` tree.

```sh
git clone https://github.com/sofus-nl/ai-native-sdlc.git
cd ai-native-sdlc
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
```

Keep changes focused, preserve cross-host compatibility, and check relative references and skill discovery in both hosts. Keep manifest versions aligned when releasing a new plugin version. Record changes in [the changelog](docs/changelogs/CHANGELOG.md). Open an issue with a concrete example or a pull request with the problem, change, and verification evidence. Do not include secrets or private project data.

Before releasing skill changes, run the [behavior checks](docs/behavior-checks.md) for risk routing, reuse, authorization, diagnosis, stopping, and delegation. The fixture generator and filesystem checker use Python's standard library; transcript review checks the agent's actual actions.

## License and acknowledgments

[MIT](LICENSE). See [third-party method references](THIRD_PARTY_NOTICES.md) for sources and attribution. This project is not affiliated with or endorsed by Anthropic, OpenAI, or the referenced framework authors.
