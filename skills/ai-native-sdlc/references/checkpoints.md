# Commit, push, and integration checkpoints

Read when planning or performing Git checkpoints. This policy does not grant permission to commit, push, open a PR, merge, or deploy.

## Establish scope once

Follow repository instructions and the user's delivery boundary. Identify the working branch, remote/destination, ownership, required checks, and push/PR-triggered workflows. Reuse existing branch and review conventions; prefer short-lived work over long-lived isolation, but do not invent a feature-branch requirement where authorized trunk work is the established practice.

Record useful checkpoints alongside existing plan tasks: coherent change, focused proof, and permitted destination. Small work may need only one commit. Do not create a separate checkpoint system, timer, commit quota, or lifecycle files for Fast work. Existing authorization can cover repeated checkpoints within its stated scope; ask only when authority or effects would expand.

## Commit a coherent increment

- After the task diff meets its acceptance criteria and focused checks pass, commit the logical increment when authorized. Include the related tests and necessary documentation; keep unrelated changes separate. Do not wait for an entire multi-step feature if an independently useful increment is ready.
- Inspect status, the staged diff, and the relevant working-tree diff. Stage only intended paths or hunks; exclude secrets and unrelated user work. Verify the staged snapshot is the change tested: unstaged dependencies or a mixed index can make a green working-tree test misleading. If evidence does not cover the commit, resolve the staging boundary or test that snapshot before claiming it passed.
- Use repository commit-message conventions and explain intent. Preserve published/shared history; do not amend another contributor's work. A needed, authorized local recovery checkpoint may preserve incomplete work, but label its failures and missing proof; it is not a verified increment or merge-ready result.

## Push for sharing or validation

- Push an authorized working branch when a useful checkpoint needs remote CI, feedback, backup, or handoff. Run available fast relevant checks and inspect intended outgoing changes first. Remote-only checks can remain pending; do not require their success before the push that starts them. Report known failures or missing validation, and share unfinished work as draft when PR creation is authorized and appropriate.
- Check outgoing commits as well as the latest diff: previously committed secrets or unrelated changes are still published. Confirm the exact remote and branch. Inspect push/PR side effects; if the action deploys, publishes a package, or exposes data outside the authorized scope, stop for the additional authority. Draft PR status does not prevent those effects.
- Keep one integration owner. Workers may commit in distinct authorized worktrees, but do not race shared-index operations or pushes to one branch. Integrate their current changes and rerun the relevant combined checks.
- On a rejected or ambiguous push, inspect remote state before retrying. Never force-push automatically. Rewriting an owned branch requires authorization, coordination, and an explicit expected remote revision if using a lease; a lease does not make overwriting collaborators safe.
- Verify the remote destination contains the intended commit and record its revision. A successful push is not proof that CI passed or anything deployed. If the remote advanced, distinguish ancestry from exact-tip equality rather than overwriting it to match local HEAD.

## Integrate and release

Before merge or a direct push to the integration branch, require the applicable checks and reviews for the current combined change. New changes or conflict resolution invalidate affected evidence. Follow branch protections and the repository's merge strategy; do not bypass them. Keep the integration build healthy; fix or revert failures only within existing authority. A merge queue is an existing repository mechanism to use when configured, not a dependency to add automatically.

Version and publish only at an authorized release boundary using [semver.md](semver.md), not at every progress checkpoint. Deployment still needs its own applicable approvals and artifact/canary proof. Report commit, push, CI, merge, and release status separately; record concise evidence in existing state or release records, not a second journal.

Sources: [Git commit guidance](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project), [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow), [DORA trunk-based development](https://dora.dev/capabilities/trunk-based-development/). The checkpoint distinctions above are this plugin's application of that guidance, not a guarantee of correct execution.
