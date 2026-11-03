---
name: agent-worktree-lifecycle
description: Coordinate a tracked task across isolated Git worktrees and scoped non-Git configuration, with verified dev delivery and separately approved main promotion.
managed-by: megai
---

# Task worktree lifecycle

Plane owns the task identity; the parent owns integration and self-review. A task may affect several repositories, but never create a new project or repository just for coordination. Every Git source writer uses a separate task-owned worktree from the repo's current dev (or an explicitly approved target); never edit/stage/commit task source in dev/main. No specific agent runner or workspace manager is required.

## Before Git edits

For each affected repo, record primary/common-directory identity, base commit, branch (e.g. `task/slug`), worktree path, owned files and acceptance in the existing Plane item. Check existing worktrees and branches for collisions and active/foreign ownership. Create a new worktree with Git's ordinary worktree command or a safe available manager; verify its actual Git identity, branch and base SHA. Reuse only a proven task-owned worktree. If identity or exclusive ownership is uncertain, block Git writes rather than fall back to dev/main. Worktrees isolate files/indexes, not shared refs, ports, processes or credentials.

## Non-Git configuration

Use an explicitly owned local configuration scope with one writer. Inspect for overlapping edits, privately back up existing files and verify the backup. Do not use `git init`, a fake checkout or an external workspace registry to satisfy isolation. Do not edit symlinks, secrets or production settings without their own authorization. The config scope itself is not a sandbox or lock.

## Delivery

Preserve parent self-review and mode-appropriate acceptance for all affected repos and configuration scopes before the first dev mutation: routine Pi uses focused tests and parent self-review; guarded Pi (including multi-repo delivery) requires the formal gate and parent self-review. Other harnesses retain their own review rules.

Run focused tests, inspect the complete diff and obtain source-current guarded acceptance when required. Commit owned Git changes in their worktrees before final evidence capture. Multi-repo readiness requires every affected repo and cross-repo compatibility. Reserve all integration targets atomically with `megai queue` under the same Plane pair and follow its published contract; unavailable queue blocks integration, not isolated work. Recheck exact candidate/target SHAs, clean target and ownership. Merge ready task commits into local dev without another approval; preserve ignored-file collisions in verified private backups. A moved base/conflict requires reconciliation and fresh checks in the task worktree. Record partial delivery and stop affected integrations rather than force/reset/replay them. Push and main promotion require separate explicit approval. Push only with normal non-force pushes and exact remote-head verification. For Pi, only approved `main` pushes publish GitHub release notes, plus Forgejo only for ADAM (see Release notes for main pushes (Pi)). Other branch pushes do not create releases.

## Safe cleanup and handoff

After verified delivery, inventory tracked/untracked/ignored data; preserve required evidence and ignored files in a private verified backup. Release any owned writers/services. With integration reservation still held, prove the recorded task commit is an ancestor of the delivered target, recheck the branch tip and worktree identity, and remove only a released, clean, task-owned worktree via normal Git worktree removal. After verifying it is gone from Git's worktree list and disk, delete only its proven-merged local task branch via `git branch -d`. Do not use force, delete a primary checkout, sweep unknown branches, or remove foreign/dirty/busy resources. A refusal retains resources and is reported separately from delivery success. External workspace bookkeeping is optional and must never substitute for Git or ownership proof. Preserve historical receipt paths.

Record the exact delivered repo/commit vector, checks, review, cleanup or retention reasons on the same Plane task and hand off In Review. Main requires explicit approval of the reviewed repo/commit vector; a changed ref or scope invalidates approval. Done requires verified main delivery. For approved main pushes follow **Release notes for main pushes (Pi)** below; no release for dev/task pushes.

## Release notes for main pushes (Pi)

Pi delivery policy: release notes are **main-only**. Only an approved push to
`refs/heads/main` triggers the release workflow below. Pushes to `pi`, `dev` and
`task/...`, any other branch, or tags alone do not create releases, release notes
or snapshot tags, and need no release-specific preflight. For mixed-ref pushes,
only the `main` ref gets a release. Normal push approval and remote-head verification
still apply to every pushed ref. Preserve existing releases and historical journals;
do not backfill non-main releases.

Push approval names the exact destinations, refs and the release/tag publication
authority; this rule grants no main/push approval. Required release destinations are
GitHub for every project, plus Forgejo only for ADAM and its component repositories.
Resolve ADAM membership from the verified existing umbrella project identity and
documented repository mapping (`ADAM full` in Plane); component repositories and
linked worktrees inherit that identity. Never infer ADAM membership from a branch
name, checkout basename or remote alias. Ambiguous identity is BLOCKED before
selecting destinations.

Non-ADAM projects (including SPMAPP and MEGAI) use GitHub only under this rule;
missing Forgejo does not block them. Do not preflight, create or register Forgejo
resources for non-ADAM projects. This scope rule grants no new push destination.

**Notes-only releases are sufficient.** Publish only the release body; do not upload
release assets. Do not build, package or upload binaries, archives, checksums or
evidence bundles solely to populate release
assets; missing attachments are not a blocker. Required tests and commit/tag/release
verification below still apply. Forge-generated source archives may appear
without manual uploads; leave them and any existing release assets unchanged.

Before a qualifying main push, preflight only the required destinations for authenticated access
and the existing target repo identity/remote, then draft the notes. A missing, unmapped or
unauthorized required forge is BLOCKED; never treat it as success, invent a
project/remote or expose private code to a new host. A queue reservation is not push
approval; the existing main/push approval boundary is unchanged.

1. Publish a **Release** for the same pinned commit on every required destination -
   release bodies, not merely commit or PR text. Record each destination's old/new
   full SHA and ref and summarize the actual verified pushed range. On a new ref, push
   from an explicitly selected baseline or a clearly identified initial-history scope;
   never assume `HEAD^`. A no-op (`old == new`) skips a new release but still
   reconciles any previously pending note.
2. Main pushes publish a notes-only **prerelease** snapshot, never latest. Tags
   follow the agreed release convention; never guess or increment a semantic version.
   The branch snapshot tag is
   `push/<ref-digest>/<full-new-commit-SHA>`, where `ref-digest` is the full 64
   lowercase hex SHA-256 of the exact fully qualified ref name's UTF-8 bytes (e.g.
   `refs/heads/main` -> `f921bd05e68b03740c450e565e0e6173e546193170b2dd404ddb6f153e9b5bf3`),
   with no newline, truncation or normalization. Look up an existing release by tag
   before creating; a conflicting tag identity is BLOCKED.
3. Group the whole approved push under one persisted push journal ID, created before
   any mutation and reused on every retry. Inside it keep one deterministic per-ref
   publication identity for `refs/heads/main`: the exact fully qualified ref plus
   its intended peeled commit, using the main snapshot tag above. Non-main refs in
   the same push have no release publication entry.
   Reuse that same per-ref identity on all required destinations and every retry; never mint a fresh
   ID for missing-side recovery.
4. Verify the remote ref first, then publish and read back the exact target commit,
   release bodies, status, the tag's peeled commit and URLs. A tag's peeled commit
   must equal the intended immutable commit; only a branch/ref target may move. An
   uncertain release create is reconciled by tag lookup before any retry.
5. Write short, simple release notes in plain language. Use a few brief bullets
   with meaningful emoji labels: ✨ changes, 🐛 fixes, ✅ actual tests, ⚠️ breaking
   changes/migration or risks, and 🔗 safe source links when useful. Include only
   relevant items; omit empty sections, boilerplate and long technical narratives.
   Emojis accompany clear text, never replace it. Preserve material warnings and
   required migration steps even when brevity needs an exception. Keep full SHA
   vectors and operational logs in the push journal rather than bloating the notes.
   Never copy secrets, PII or private tracker content into release notes.
6. An uncertain or partial push/publication stops and reconciles read-only: preserve
   the journal and queue, keep any published success on one forge, report push success
   separately from release failure, never roll back a successful push, and resume only
   the missing required destination without re-pushing successful refs, duplicating releases or
   overwriting human-written text.

This is agent instruction, not enforcement: MEGAI installs no git hook, and manual
pushes outside this workflow are not intercepted.
