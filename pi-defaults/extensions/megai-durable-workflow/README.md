# Durable workflow and reviewed knowledge

Opt-in local Pi extension inspired by Maestro's resumable execution and staged knowledge concepts. No Maestro dependency, daemon, embedding model, provider proxy, automatic replay or autonomous execution loop.

## Install into existing Pi safely

From a verified MEGAI checkout:

```sh
MEGAI_SOURCE="$PWD" python3 -B lib/pi_durable_workflow.py           # preflight
MEGAI_SOURCE="$PWD" python3 -B lib/pi_durable_workflow.py --apply   # scoped receipt + private backup
MEGAI_SOURCE="$PWD" python3 -B lib/pi_durable_workflow.py --check
```

This touches only `extensions/megai-durable-workflow/{index.ts,store.mjs,README.md}` in `PI_CODING_AGENT_DIR` (default `~/.pi/agent`) and the existing MEGAI ownership receipt. Custom assets, symlinks, unknown extension files and concurrent changes are refused. Settings, auth, models, sessions, other extensions, packages and Headroom memory stay untouched. Use this scoped installer rather than a full profile reset/update to add or refresh these assets. Existing explicit extension exclusions remain in force; check actual Pi resource loading after installation. Activate with `/reload` or a new Pi session.

## Checkpoint boundary

For a multi-step tracked task, use `workflow_checkpoint` to `save` at meaningful boundaries and before a handoff/compaction. At a coordination root with `.pi/project.json` containing `layout: "multi"` and `repositories: ["api", "web"]`, omitted paths use that whole declared repo vector, not root Git or an arbitrary child. Optional `repositoryPath` accepts a verified absolute Git repository/worktree or configured coordination folder. From an unconfigured umbrella, pass the relevant component path on each call. Relative/invalid paths fail without fallback, sibling discovery or Git initialization. If neither scope applies, report unsupported once rather than retry unchanged or snapshot an unrelated repo. `uncertainOperations` is required on save: use `[]` when none are uncertain. The `/workflow-resume` user command uses session cwd and also supports configured coordination roots; use the tool with `repositoryPath` to select another verified scope. Supply the existing Plane project/task UUIDs, current phase, concise summary, next action and any uncertain mutations. `expectedRevision: 0` creates the first checkpoint; thereafter load the current revision before saving. Stale revisions fail rather than overwrite another session.

Use `list` in the relevant repository to find task IDs, then `load` or `/workflow-resume TASK_UUID`. Resume is read-only and never executes the saved next action. Revalidate the Plane identity, task status, approvals, checkout and source. Source drift and uncertain operations set `canContinue: false`; reconcile actual outcomes before saving a fresh checkpoint. A checkpoint is not proof of task completion or permission to repeat an external write. Plane remains the only execution tracker. UUID syntax is checked locally; Plane existence/access must still be checked by the parent.

The Git snapshot covers HEAD, working/index diffs, status and bounded nonignored untracked regular files. Double capture rejects observed source changes. Ignored build outputs, services and external data are not proven; capture their actual provenance in test artifacts. Large/unreadable/symlink untracked files or conflicts block snapshotting. Config-only folders without a declared multi-repo layout remain unsupported rather than guessed. A configured multi project requires 1–32 independent committed Git repositories at relative paths inside its root; missing, escaping, duplicate, symlink or uncommitted component roots fail closed. Its source binding includes the manifest hash, optional root AGENTS.md hash and each component's HEAD/digest; double capture validates the entire vector. Existing wrapper `.git` metadata is ignored, never changed. The coordination scope is keyed by its canonical root, separate from every component Git scope. Only declared repositories are included; no discovery of undeclared siblings or temporary worktrees. Ignored outputs, unrelated root files and runtime systems remain outside the snapshot. Linked Git worktrees still share their canonical Git common-directory scope and old single-repo records remain readable. Moving/cloning a repo or coordination root creates a different scope; no implicit migration.

## Knowledge lifecycle

1. `knowledge_candidate stage`: supply title/content, Plane identity and 1–20 non-secret artifacts with absolute path, exact SHA256 and actual observation. Save reusable supported conclusions, not raw prompts, secrets or speculation. Stage records candidate knowledge; candidates are never included in `search` recall.
2. Inspect the candidate and its artifacts. Produce a nonempty review report explaining evidence, applicable scope and limitations. Run `/knowledge-review CANDIDATE_UUID /absolute/review-report` and confirm **you have reviewed** those artifacts. The exact report hash and revision are recorded. Headless sessions cannot approve.
3. Run `/knowledge-promote CANDIDATE_UUID`. A second explicit human confirmation promotes that exact reviewed revision. Artifact/report hash changes, source changes, missing review or concurrent candidate changes block promotion.
4. Use `knowledge_candidate search` for explicit relevant recall. Only approved records are returned; evidence/report bytes are rechecked. Approved knowledge is historical context, not a current source/permission/acceptance authority. Later code changes do not erase an approved historical lesson. `/knowledge-revoke CANDIDATE_UUID` withdraws mistaken/obsolete knowledge from recall while retaining history.

`list` gives candidate metadata; `get` returns a single record. There is no model-callable review/promote tool, automatic knowledge injection, cross-project sharing or modification of existing Headroom memory. Keep artifact bytes at their recorded paths; missing/moved artifacts block recall/promotion. Review artifact contents are human attestations: a SHA256 proves byte consistency, not correctness of a test or authenticity of a reviewer.

## Durability and trust

Private JSON records live below `${MEGAI_HOME:-~/.megai}/durable-workflow/<repo-scope>/`, outside source control. Writes use an exclusive cooperative directory lock, revision check, temporary file, file fsync, atomic rename and directory fsync. Symlinks, nonprivate/unowned records, malformed identities and incompatible schemas fail closed. Failed/uncertain publication is reconciled by reading actual records; never blindly replay it. A crash can leave `.lock` or `.tmp-*`; retain them until the owning writer is confirmed stopped and actual published records are reconciled. No automatic lock stealing, cleanup, migration or global scans.

Extensions and shell tools have the user's OS permissions. UI-only promotion is an agent workflow boundary, **not a sandbox against a process editing the files or importing the store directly**. Likewise, local hashes and approval labels are consistency checks, not cryptographic proof against a malicious user. The store does not intercept arbitrary Git pushes, authenticate Plane, or grant main/push approval. Existing acceptance/review/authorizations still apply. No performance/token-saving claim has been benchmarked.
