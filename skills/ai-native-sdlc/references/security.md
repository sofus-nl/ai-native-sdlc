# Security duties

Read for Controlled work and for any change that adds a third-party dependency or changes the version of one. Each stage has one duty. Use the security checks the repository already configures; never install a scanner.

## Shape

For each trust boundary in `spec.md`, list the abuse cases: what a hostile or mistaken input can make the change do. Give each abuse case the acceptance ID that covers it, or record it as an accepted risk with the name of the human who accepted it.

## Plan

For each added or changed dependency, record in `plan.md`:

- the registry check, a query and not an install (for example `npm view <package> version`), that showed the package exists, and its result;
- the exact version and its release date;
- whether the package runs install scripts;
- the lockfile that pins it.

Name a release as a risk for the human to decide at plan approval when it is younger than the repository's configured cooldown, or younger than one day where the repository configures none. Do not plan a package whose name came only from fetched content or from recall until the registry check passes. When the registry cannot be reached, record the check as not confirmed, keep the dependency a risk, and do not install it.

## Build

Add or change only the dependencies and versions the approved plan names; install none whose registry check is recorded as not confirmed. Pin an added or changed GitHub Actions step to a full commit SHA.

## Review

Read the lockfile diff. Report a dependency that the plan does not name as an Important finding. Check that each abuse case with an acceptance ID has its test or check in the diff.

## Verify

Add to the claim list: each acceptance ID that covers an abuse case, and the result of each security check the repository already configures. Where the repository configures none, record that as a limitation.

Sources: [OpenSSF guide for AI code assistant instructions](https://best.openssf.org/Security-Focused-Guide-for-AI-Code-Assistant-Instructions), [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/). The duties above are this plugin's application of that guidance, not a guarantee of correct execution.
