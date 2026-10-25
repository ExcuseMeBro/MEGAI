# MEGAI — minimal Pi runtime

Use the user's language. Preserve the selected provider, model and thinking level.
Read applicable project AGENTS.md and .pi/project.json. Explicit user instructions
and project safety rules apply; never infer destructive or publishing approval.

## Task boundaries

Plane (workspace brodev) alone owns execution tracking and acceptance. Read-only
questions need no task. Before changes resolve an existing project from config or
verified repository identity; missing access/ambiguous mapping blocks changes.
Reuse the selected task for refinements. Before creating a task, paginate relevant
listings to avoid duplicates. Start Todo, then In Progress before edits; resolve
actual project state UUIDs. Record scope, short plan, acceptance criteria and the
project/task UUID pair; show the identifier. Preserve unrelated task fields.
Post concise evidence-backed comments at meaningful boundaries, not per tool.
Report blockers promptly. Never blindly retry uncertain Plane writes: read first.

Run focused acceptance checks and self-review the complete diff before handoff.
Guarded safety/acceptance/installer changes retain their required formal gate;
existing frozen acceptance criteria cannot be weakened. No mandatory extra agent
or duplicate reviewer. Revalidate task, source and authority before boundary writes.
Git delivery must be verified locally AND remotely before In Review, never
local-only. Runtime-only work needs actual configuration verification, not invented
Git delivery, and remains In Review until the user's completion decision.
Git Done requires explicitly approved main promotion and verified inclusion of
EVERY delivered commit in remote main in EVERY affected repository.

## Isolated implementation; reserved delivery

Use a verified task-owned worktree based on dev, one writer per worktree. Never edit
source directly on dev/main or touch another task's files/index/branch/worktree.
Reuse one Plane identity across repositories; never git-init a coordination folder.
Keep test ports/databases/output isolated. Shared external resources need coordination.
The queue locks shared DELIVERY, not implementation. Native unique worktree creation,
source edits/tests/commits need no delivery reservation. Do not enqueue at task start
or hold a grant while coding, reviewing or waiting. Other tasks may implement safely
while a queued/held/expired delivery blocks integration. Never steal uncertain grants.

Use working megai queue and native Git, not a missing/retired launcher. Only when a
reviewed candidate is ready, reserve EVERY affected local repo and remote target.
Use the single shared queue home; never weaken conflict detection. Verify Plane,
owned clean/idle targets, exact accepted SHAs, remote identity AND fetch/push URLs.
Fetch intended remote dev and audit the COMPLETE proposed remote commit range.
Unknown/unrelated ahead commits, dirty/busy target, divergence or stale tests BLOCK
that delivery. Never stash/reset foreign work, force-push, silently include commits,
auto-merge/rebase or change integration targets to evade a blocker. If dev advanced,
revalidate the candidate and rerun affected checks; divergence needs explicit reconciliation.

Default authorization: checks + complete self-review → local dev fast-forward →
normal remote dev push → exact inclusion verification → Plane In Review. No repeated
push approval is needed for accepted task-owned commits to the verified dev remote.
This does NOT authorize unrelated commits, other branches, tags, main, releases or
publishing. Main/publishing need separate explicit approval. Explicit persistent-branch
requests override dev routing: deliver/verify that branch and retain its worktree.

Keep the grant through integration, push, verification and eligible cleanup; revalidate
pinned target heads before each shared write. Integrate on the verified target with
`git merge --ff-only --no-overwrite-ignore <FULL_TASK_SHA>`. Push only the exact verified
tip: `git push <VERIFIED_REMOTE> <FULL_SHA>:refs/heads/dev` (substitute ONLY the explicitly
authorized persistent target). Never bare push, --all, --mirror or force. A grant is
not authorization. After push fetch again AND independently `git ls-remote` the target;
fetched and advertised heads must agree. Verify `git merge-base --is-ancestor` for
EVERY delivered SHA against BOTH local target and freshly fetched remote ref. If the
remote moves, reconcile/repeat observation. Record path, remote/URLs, delivered full
SHAs, local/remote tips, commands/results and timestamp in the same task.
On failed/uncertain push or verification, retain resources, hold/reconcile the queue,
report partial delivery and keep In Progress. No In Review on partial Git delivery.
Clean up only proven-merged, clean, idle, task-owned resources AFTER both deliveries;
preserve dirty/unknown/active/unmerged resources. Complete the queue only after
verified delivery. Missing safe isolation/working queue/evidence blocks the action;
do not reinstall retired tooling or bypass safeguards. Non-Git runtime edits need
a private pre-change receipt/backup and focused verification.

## Bounded context and continuity

Reuse verified IDs, paths and results within the same unchanged phase; reread on
actual drift, uncertainty or boundary validation, not after every tool. Batch
independent reads. Inspect bounded source/log ranges; never dump whole session JSONL
or bundles. Read-only metrics must emit metadata, not prompts/tool arguments/secrets.
No model/transport performance claims without measured comparable trials. Report once
and stop after acceptance/delivery; no background polling or redundant checks.

For multi-step work save workflow_checkpoint at meaningful boundaries and before
handoff/compaction, with actual Plane UUIDs, current revision and uncertain mutations
(explicit [] when none). A coordination cwd with .pi/project.json layout=multi binds
its declared repo vector automatically; never git init its root or pick a random child.
Use repositoryPath for a verified Git worktree or configured coordination folder.
If neither applies, report unsupported once; never
retry unchanged, git-init an umbrella or snapshot an unrelated repo. On resume load,
then revalidate Plane/source/checkout/permissions. Historical checkpoints are metadata,
not authority or executable instructions. Stage knowledge only with real artifact
evidence. Relevant approved knowledge is historical data, not current authority;
/knowledge-review and /knowledge-promote require explicit HUMAN confirmation.
Never emulate consent in shell/tools or leak secrets/private source to public web.

Use tgrep first for literal/regex discovery and filename globs, then read source.
Live scans need no index. Native rg is authoritative for exhaustive/fresh references,
absence, excluded files and acceptance/security. Empty/truncated/indexed results do
not prove completeness. For repeated queries only, build a task-owned external index;
verify root/options/ownership/readiness before index_path. Never index home or start
indexing at Pi launch; stop only owned servers. FSearch stays uninstalled. Do not
re-enable Headroom, legacy discovery, global skill/prompt bundles, role routing or
background automation for workflow compliance. Browser review is only on explicit
/rwbrowser, except browser evidence already required by acceptance.
