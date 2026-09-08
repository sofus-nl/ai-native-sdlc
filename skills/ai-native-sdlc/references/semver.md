# Semantic versioning for delivered software

Normative reference: [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html), the latest published specification checked on 2026-09-08 at [semver.org](https://semver.org/). This is an application guide, not a copy or replacement of the specification. Check the official site when updating this reference; do not assume a later specification exists.

## Establish the contract

Use SemVer for versioned software delivered through this workflow. Inspect repository release policy, public API, manifests, changelog, and published versions first. The contract may include documented functions, endpoints, CLI flags, configuration, data formats, or user-visible behavior; identify the actual consumer promises instead of judging compatibility by diff size.

Reuse existing release tooling and version sources. If the project explicitly uses another scheme, report the conflict and ask before migrating it; do not silently relabel CalVer or change external API identifiers. If no public contract or pre-1.0 policy exists, propose it and resolve material uncertainty before choosing a release version. A small non-release edit does not require a version bump, new release files, or a release pipeline.

## Choose and explain

- For stable APIs, incompatible changes increment MAJOR; compatible additions and deprecations increment MINOR; compatible fixes increment PATCH. Reset lower components when increasing a higher one. Classify the complete release since its published baseline, not just the latest commit, using the highest required bump.
- Major zero denotes development, not stability. Follow the project's documented `0.y.z` convention; propose minor bumps for additions/breaks and patch bumps for compatible fixes if none exists. Do not present that convention as a SemVer requirement or silently declare `1.0.0`.
- Use valid `X.Y.Z` syntax, no leading zeroes. Prerelease numeric identifiers also forbid leading zeroes. Prereleases precede the associated normal version; build metadata does not increase precedence. Check ordering with existing SemVer-aware tooling, never lexical string ordering.
- Record current -> proposed version, affected public contract, compatibility evidence, and any migration/deprecation note in the existing plan or release record. Tests passing alone do not establish compatibility. Documentation-only packaged releases still need a new version; follow repository policy for the increment.

## Verify before shipping

Check all affected version sources, generated metadata/lockfiles where applicable, and release notes agree using the repository's tooling. Check the proposed version against the authoritative history and baseline of the selected release line, including prereleases; do not reuse an existing published version. Maintenance releases on an older line remain valid after a newer major release. Missing history access is a verification gap, not proof a version is unused.

Never change the contents of an already released version, move its tag, or republish it under the same version. A cachebuster or mutable branch name is not a new release. Publication requires the existing release authorization and gates; preparing a version does not authorize committing, tagging, pushing, or deploying. After authorized publication, verify the version and revision of the actual artifact, not only the source manifest.
