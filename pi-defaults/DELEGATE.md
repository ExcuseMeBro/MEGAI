# Pellet delegation (opt-in)

`/delegate all` or `/delegate <PELLET_UUID>,<PELLET_UUID> concurrency=2`
starts independent existing MEGAI Pellet tasks (max 20 per request, 1–4 Pi-Bolt
workers concurrently). The command is registered by `megai-factory/index.ts`;
legacy `/factory` remains the frozen Plane-only runner. Only `/splane` syncs.

The parent verifies the repository ↔ Pellet folder and task acceptance, then
`factory_delegate` requests interactive confirmation. It queries every page,
reserves fresh private receipts, creates **new** task-owned worktrees from a
pinned local `dev` SHA serially, starts one `pi-bolt` child per task with the
selected provider/model/thinking and `--no-mcp`, and waits for each exit. A
refused/uncertain worker is **not** retried. The receipt and private worker log
are in `~/.megai/factory-workers/` as `<PROJECT>-<PELLET_UUID>.json` and
`<PROJECT>-<PELLET_UUID>-events.jsonl`; task worktrees are siblings
of the repository. Existing worktrees, receipts and dirty dev block selection.
A failure retains the worktree, branch, log and receipt for reconciliation.

Leaf workers implement/test/review/commit only; they cannot accept tasks,
merge, push, clean up or terminate user sessions. The parent inspects and tests
every resulting branch, then serializes shared dev delivery under AGENTS.md:
verified exact SHA in local AND freshly fetched/advertised remote dev, eligible
cleanup attempt immediately after complete delivery, and Pellet `in-review` only
when appropriate. Exit 0 alone is not success. The tool does not implement OS
sandboxing; use it only for genuinely independent tasks with non-overlapping
external resources. Project identity ambiguities, unresolved dependencies,
missing acceptance or shared writes must be handled before delegation.

For this Pi-Bolt profile, install only the two `megai-factory/` extension files
into its extension directory after a private pre-change receipt/backup and
verify `/delegate` via a fresh read-only RPC probe. Do **not** run the old full
`pi-defaults/install.py`: it still installs retired Headroom/search tooling.
The tool starts only when `/delegate` is invoked and confirmed. Reload the
extension in a user-controlled session when ready; never restart or close an
active user session to enable it.
