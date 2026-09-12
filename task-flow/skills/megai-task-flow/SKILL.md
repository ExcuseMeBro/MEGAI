---
name: megai-task-flow
description: Start and label tracked project changes, then hand off verified work in Plane. Parent-only; questions and read-only investigation need no task.
managed-by: megai
---

# Plane-only task flow

Plane owns task identity, acceptance, execution notes and status. The parent loads this skill once at task start/resume; children inherit the `(project UUID, work item UUID)` pair and never mutate Plane or launch agents.

## Start boundary

1. Reuse the active identity for refinements. Otherwise resolve the Git root and consume every Plane project page; require exactly one exact Git-root folder-name match. A managed worktree inherits its parent's project identity. Zero/multiple matches require the user; never create a project implicitly.
2. Consume every workflow-state page. Require exactly one `In Progress` and one `In Review`, both `group=started`, before mutation. Failed/incomplete responses, missing states or ambiguity block edits.
3. Reuse a known work-item pair directly. Otherwise consume every project work-item page and compare the exact requested title. One match: reuse; multiple: ask. Zero matches after a successful complete lookup: automatically create exactly one item without asking for approval at step 4, using that exact title and the resolved `In Progress` state UUID. Failed or incomplete lookup is never zero matches. For a supplied historical Asana identity, match both `external_id=GID` and `external_source=asana-migration-v1`; zero/multiple matches block reconciliation, never create a replacement. Preserve historical source identity/markers until the Plane pair is confirmed.
4. Resolve the required labels using **Task labels** below before creating/updating the item. Create with resolved label UUIDs and `In Progress`, or update the existing item to `In Progress` once and add only missing labels. Inspect the returned state and read back labels before project edits. Reconcile an uncertain write by lookup before retrying; never duplicate it. Retain the returned pair in session context. Acceptance belongs in that Plane item, not a second execution board.

Unavailable or unauthenticated Plane blocks project edits. Pure questions/read-only work need no mutation. Resume with the known pair; fetch when its boundary state or labels need verification.

## Task labels

Apply at task start and resume/refinement, and recheck at handoff when scope changed.
The parent owns classification and label writes; children only report scope changes.
This is agent workflow policy, not an API hook or automatic bulk backfill.

### Classification

Choose exactly one primary type by the requested outcome, not incidental files:

| Type | Use when |
| --- | --- |
| `bug` | Restore broken intended behavior, including regressions |
| `feature` | Add or intentionally change user/product capability |
| `refactor` | Restructure without changing observable behavior |
| `docs` | Change documentation, agent instructions or policy only |
| `test` | Add/change verification only; no product behavior change |
| `chore` | Maintain dependencies, configuration, builds or routine tooling |
| `research` | Deliver a requested tracked investigation artifact; a read-only question still needs no task |

Choose one or more affected areas supported by the task scope:

| Area | Scope |
| --- | --- |
| `backend` | Server logic, APIs, jobs and services |
| `frontend` | Browser UI and web client behavior |
| `mobile` | iOS, Android, Flutter or React Native apps |
| `desktop` | Desktop applications and native desktop integration |
| `infra` | Deployment, CI/CD, hosting and observability infrastructure |
| `data` | Schemas, migrations, storage, analytics and data pipelines |
| `design` | UX/UI specifications, interaction and design-system work |
| `tooling` | Developer tools, agent workflows, repository automation and local harness configuration |

Use all affected areas for cross-stack work (`backend` + `frontend`, not an invented
`fullstack` substitute). A bug with a regression test stays `bug`; a feature with
internal cleanup stays `feature`. Standalone instruction changes are `docs` +
`tooling`; a mobile API feature is `feature` + `mobile` + `backend`. If intent or
area is genuinely unclear, ask before mutation instead of guessing or using `chore`
as a fallback. Split independently deliverable mixed outcomes, not incidental work.
Optionally add `security`, `performance` or `accessibility` only when explicit
acceptance covers that concern; they do not replace a primary type or area.
Priority, workflow state, assignees and release/version stay in their native fields.

### Resolve and attach safely

1. Consume every project label page in the resolved workspace/project. Match names
   by trimmed, case-insensitive equality; reuse the unique existing label UUID.
   Respect an explicitly documented project mapping (e.g. `type:bug`, `area:backend`)
   instead of creating parallel spellings. Never infer aliases or use IDs from another
   project. Multiple matches, conflicting mappings, failed/incomplete pages or missing
   label permissions are BLOCKED before project edits, not an empty catalogue.
2. Only after a complete lookup proves zero matches, create the needed canonical
   lowercase label in that project with a short taxonomy description. Create only
   labels needed by this task, not the whole catalogue. Reconcile a timeout, conflict
   or uncertain create by a fresh complete lookup before retrying; a still-uncertain
   result is BLOCKED. Reuse a unique concurrent creation; never blindly retry.
3. Retrieve the existing item's labels before changing them. Preserve unrelated/custom
   labels, their metadata and historical external identity. If an existing primary
   type contradicts the requested outcome, ask for reconciliation; do not silently
   remove it or attach a second primary type. Existing area labels inconsistent with
   the new scope also need reconciliation rather than silent removal.
4. For a new item, pass resolved UUIDs in `labels` during create. For an existing item,
   use additive `manage_label` with `add_label_id` for missing UUIDs only; never replace
   the whole `labels` array. If additive mutation is unavailable, BLOCKED rather than
   a read/replace race. Read back the item and verify the required UUIDs are attached,
   prior labels remain and there is exactly one mapped primary type. Unexpected drift
   or uncertain attachment requires read-only reconciliation before any retry.
5. Reuse that item and classification on resume when scope is unchanged. Reclassify
   only on evidenced scope change using the same checks. No routine label polling,
   global renaming/deletion, unrelated task relabeling or bulk backfill; those require
   a separate explicit user request.

## Execute and hand off

- Inspect, implement, self-review, and verify observable acceptance with relevant tests. Security/data-integrity risks or consequential cross-module changes require independent review. Preserve accessibility, compatibility and error handling.
- Reuse the active pair throughout refinements. Keep only boundary writes: no routine stage sync, milestone comments, polling, second tracker or automatic queue draining.
- Complete the user's agreed branch delivery before handoff. Default worktree delivery uses `agent-worktree-lifecycle`; an explicitly requested persistent branch is pushed and retained without merging into other branches.
- At verified handoff, record concise evidence/remaining risks on the same item and move it to started `In Review`. Keep it incomplete; do not invent a completion boolean. Only the user may move it to `Done`.
- Main promotion requires separate explicit user approval. Stop after the requested task.
