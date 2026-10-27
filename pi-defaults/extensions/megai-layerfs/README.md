# Pi-Bolt LayerFS task bridge (MEGAI)

This extension routes Pi-Bolt's **built-in** `read`, `write`, `edit`, `bash` and
interactive `!` shell commands to one real Linux LayerFS Workspace when Pi
starts in a verified MEGAI Pellet task-owned Git worktree. It never replaces
Pellet tracking or the canonical Git delivery policy. It blocks other Pi
model tools in an active task session except Pellet task tracking; use routed
`bash` for search. It does not make a Mac filesystem mount or OS-level
sandbox, and cannot cover external processes, arbitrary Pi plugins or a
session in `dev`/`main`. Do not describe it as a universal per-task default.

A branch named `task/factory-<32-char Pellet UUID>` or
`task/layerfs-<32-char Pellet UUID>` binds automatically. The legacy/manual
`task/layerfs-<first 8 chars>` branch needs `MEGAI_PELLET_TASK_ID=<full UUID>`
in that Pi process's environment. All other non-`dev`/`main` Git branches and any Git checkout with uncertain
identity are **blocked**, not silently routed to the host. A directory outside
Git is left as a local, non-task session. Project identity and clean task worktree,
branch, dev ancestry and exact origin fetch/push URLs are checked before the
first import. An existing dirty worktree or concurrent/uncertain session
blocks attachment.

Pinned prerequisites for this host: upstream LayerFS v1.1.0 commit
`9f97a7ec95b662e9cb288704afa165feff132cfa`, built source and native
addon under `/Users/bro/.local/share/layerfs-task-73fddf83/source`, sealed
Linux bundle under that task's `build-resources/`, and Docker image digest
`sha256:c966e68bc796a95855bb565f0dc7366b89f2ce73c265dbc00662dfe49b302f89`.
The task-private root, workspaces and state receipts must be retained while
this extension is installed. Never run the retired full `pi-defaults/install.py`
to install it. Install only these two files to a new, privately backed-up
`~/.pi/agent/extensions/megai-layerfs/` after all focused checks and a
complete self-review. Existing Pi sessions remain untouched; a new session
loads the extension, or the user may explicitly `/reload` their own session.

A Pi session checkpoint is committed to LayerFS on exit, **not** to durable
Git. LayerFS Store uses Disposable WAL settings, so a Docker/host crash can
lose changes until durable Git handoff. After committing accepted work *inside*
the Workspace, end that task session, then from the trusted Mac parent run
`client.mjs` with `{"action":"export","taskId":"<UUID>"}` on stdin. It
refuses dirty/diverged Git, checks lineage, checkpoints the Workspace, creates
an exact Git bundle under the task-private receipts and verifies its head and
prerequisite. **Export alone does not update the host worktree or dev.** The
parent must audit the full commit range and independently validate/fast-forward
only the correct task-owned worktree using native Git, then perform the normal
verified dev delivery and mandatory cleanup flow. Never fetch/merge a proof
fixture commit into dev. On an unknown operation, retain the receipt, lock,
worker, Workspace and worktree for manual reconciliation; do not replay.

Focus checks: `MEGAI_LAYERFS_TEST_LIVE=1 node --test tests/pi-layerfs-bridge.test.mjs`
from the verified task-owned source worktree. `client.mjs` accepts one JSON
request on stdin and returns one JSON reply (failures have `ok:false` and exit
nonzero); it is not an open network service. Benchmark fixture and raw samples
are private to the Pellet task, not runtime speed guarantees.
