# Versioning and compatibility

The SDLC applies [the shared SemVer reference](../skills/ai-native-sdlc/references/semver.md) to delivered projects. This document defines this plugin's own contract and release procedure.

## Public API

The compatibility contract comprises:

- Plugin and marketplace identifiers and the nine skill names listed in the README.
- Each skill's documented purpose, supported invocation, scope, and authorization boundaries.
- Fast/Standard/Controlled lane behavior, required approvals, verification requirements, and the documented artifact paths and fields in [artifact-contracts.md](../skills/ai-native-sdlc/references/artifact-contracts.md).
- The documented Claude Code and Codex packaging and installation interface.

Prompt wording, internal reference layout, research notes, and development helpers are implementation details unless another documented public contract requires them. Exact generated prose, deterministic model behavior, token savings, and unsupported host features are not compatibility guarantees. A wording change that alters the contract is still a behavioral change.

## Choose the version

Apply the shared reference's stable-release rules from `1.0.0` onward.

During `0.y.z`, the API is explicitly unstable. Our project convention is a minor bump for additions or breaking changes and a patch bump for compatible fixes or documentation-only releases. Label breaking changes and migration steps in the changelog. This is our convention, not a SemVer requirement for major-zero releases. Declare `1.0.0` only when committing to a stable public API.

Examples: adding model-selection guidance without removing existing behavior is `0.4.0 -> 0.5.0`; fixing that guidance compatibly is `0.5.0 -> 0.5.1`. Removing or renaming a skill requires a new minor version while pre-1.0, or a major version after 1.0.

Verify host support before distributing suffixed versions; a local cachebuster is not a release version increment.

## Release checklist

1. Review the public contract diff and choose the appropriate bump. Keep `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` versions identical. The marketplace currently has no duplicated version; if an entry version is introduced, it must match too.
2. Keep the pending version under `## <version> - Unreleased` in the changelog. Complete required validation and cross-host behavior checks before dating that entry `YYYY-MM-DD`. An unreleased entry or manifest bump is not a release claim.
3. Run `python scripts/check_version.py`, `python scripts/check_version.py --self-test`, `python scripts/test_behavior_check.py`, package validation, and the [behavior checks](behavior-checks.md). The version checker covers syntax and consistency only, not whether the selected bump matches behavior or whether a release is qualified.
4. When release publication is authorized, commit the exact validated package and create an immutable `v<version>` tag. Check existing remote tags/releases first; never move or reuse a published tag or overwrite an existing version's package. Any subsequent package-content change needs a new version. Do not rewrite historical releases to conceal an earlier versioning mistake.
5. Treat `main` as a mutable development channel, not an immutable release. Use the release tag or its exact commit for reproducibility where the host supports selecting a ref. Report installation and runtime verification separately from publishing.

Historical limitation: model-selection changes reached `main` with `0.4.0` still in the manifests. Preparing `0.5.0` corrects future packaging; it cannot retroactively make earlier same-version snapshots immutable.
