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

For a multi-step tracked task, use `workflow_checkpoint` to `save` at meaningful boundaries and before a handoff/compaction. From a non-Git umbrella, pass `repositoryPath` (the verified absolute relevant Git repository/worktree path) on each tool call; omitted paths use session cwd. Relative/invalid paths fail without fallback or Git initialization. If no relevant Git repo exists, report unsupported once rather than retry unchanged or snapshot an unrelated repo. `uncertainOperations` is required on save: use `[]` when none are uncertain. The `/workflow-resume` user command still uses session cwd; use the tool with `repositoryPath` when outside Git. Supply the existing Plane project/task UUIDs, current phase, concise summary, next action and any uncertain mutations. `expectedRevision: 0` creates the first checkpoint; thereafter load the current revision before saving. Stale revisions fail rather than overwrite another session.

Use `list` in the relevant repository to find task IDs, then `load` or `/workflow-resume TASK_UUID`. Resume is read-only and never executes the saved next action. Revalidate the Plane identity, task status, approvals, checkout and source. Source drift and uncertain operations set `canContinue: false`; reconcile actual outcomes before saving a fresh checkpoint. A checkpoint is not proof of task completion or permission to repeat an external write. Plane remains the only execution tracker. UUID syntax is checked locally; Plane existence/access must still be checked by the parent.

The Git snapshot covers HEAD, working/index diffs, status and bounded nonignored untracked regular files. Double capture rejects observed source changes. Ignored build outputs, services and external data are not proven; capture their actual provenance in test artifacts. Large/unreadable/symlink untracked files or conflicts block snapshotting. This initial version requires a Git repository; config-only/non-Git checkpoints are unsupported rather than guessed. Linked worktrees share a scope identified by canonical Git common-directory path; another repo cannot recall these records. Moving/cloning a repo creates a different scope; no implicit migration.

## Knowledge lifecycle

1. `knowledge_candidate stage`: supply title/content, Plane identity and 1–20 non-secret artifacts with absolute path, exact SHA256 and actual observation. Save reusable supported conclusions, not raw prompts, secrets or speculation. Stage records candidate knowledge; candidates are never included in `search` recall.
2. Inspect the candidate and its artifacts. Produce a nonempty review report explaining evidence, applicable scope and limitations. Run `/knowledge-review CANDIDATE_UUID /absolute/review-report` and confirm **you have reviewed** those artifacts. The exact report hash and revision are recorded. Headless sessions cannot approve.
3. Run `/knowledge-promote CANDIDATE_UUID`. A second explicit human confirmation promotes that exact reviewed revision. Artifact/report hash changes, source changes, missing review or concurrent candidate changes block promotion.
4. Use `knowledge_candidate search` for explicit relevant recall. Only approved records are returned; evidence/report bytes are rechecked. Approved knowledge is historical context, not a current source/permission/acceptance authority. Later code changes do not erase an approved historical lesson. `/knowledge-revoke CANDIDATE_UUID` withdraws mistaken/obsolete knowledge from recall while retaining history.

`list` gives candidate metadata; `get` returns a single record. There is no model-callable review/promote tool, automatic knowledge injection, cross-project sharing or modification of existing Headroom memory. Keep artifact bytes at their recorded paths; missing/moved artifacts block recall/promotion. Review artifact contents are human attestations: a SHA256 proves byte consistency, not correctness of a test or authenticity of a reviewer.

## Durability and trust

Private JSON records live below `${MEGAI_HOME:-~/.megai}/durable-workflow/<repo-scope>/`, outside source control. Writes use an exclusive cooperative directory lock, revision check, temporary file, file fsync, atomic rename and directory fsync. Symlinks, nonprivate/unowned records, malformed identities and incompatible schemas fail closed. Failed/uncertain publication is reconciled by reading actual records; never blindly replay it. A crash can leave `.lock` or `.tmp-*`; retain them until the owning writer is confirmed stopped and actual published records are reconciled. No automatic lock stealing, cleanup, migration or global scans.

Extensions and shell tools have the user's OS permissions. UI-only promotion is an agent workflow boundary, **not a sandbox against a process editing the files or importing the store directly**. Likewise, local hashes and approval labels are consistency checks, not cryptographic proof against a malicious user. The store does not intercept arbitrary Git pushes, authenticate Plane, or grant main/push approval. Existing acceptance/review/authorizations still apply. No performance/token-saving claim has been benchmarked.
