# Pellet delegation (opt-in)

`/delegate all` or `/delegate <PELLET_UUID>,<PELLET_UUID> concurrency=2`
starts independent existing MEGAI Pellet tasks (max 20 per request, 1–5 native
Paseo Pi agents launched concurrently). The command is registered by `megai-factory/index.ts`;
legacy `/factory` remains the frozen Plane-only runner. Only `/splane` syncs.

The parent verifies the repository ↔ Pellet folder and task acceptance, then
`factory_delegate` requests interactive confirmation. It queries every page,
reserves fresh private receipts, creates **new** task-owned worktrees from a
pinned local `dev` SHA serially, then creates a visible, separate Paseo local
workspace bound to each worktree and launches one native Pi **agent tab** and
one **terminal** in it. The selected provider/model/thinking must be supported
by Paseo or the request is refused before any worktree write. Launches are
asynchronous: the command returns agent, workspace and terminal IDs, **not** a
completion verdict; each agent may continue working in its own Paseo view.
A refused/uncertain launch is **not** retried or stopped. The receipt and
private launch-stage log are in `~/.megai/factory-workers/` as
`<PROJECT>-<PELLET_UUID>.json` and `<PROJECT>-<PELLET_UUID>-paseo.jsonl`;
task worktrees are siblings of the repository. Existing worktrees, receipts
and dirty dev block selection. A failure retains the worktree, branch,
workspace/agent/terminal if created, log and receipt for reconciliation.

Leaf agents are instructed to implement/test/review/commit only; they must not
accept tasks, merge, push, clean up or terminate user sessions. A Paseo terminal
is an idle shell for inspecting its agent's worktree, not a second automatic
writer. The parent checks each agent's actual completion and inspects/tests
every resulting branch before serializing shared dev delivery under AGENTS.md:
verified exact SHA in local AND freshly fetched/advertised remote dev, eligible
cleanup attempt immediately after complete delivery, and Pellet `in-review` only
when appropriate. Agent creation/idle status alone is not success; never remove
a workspace or session to unblock delivery/cleanup. The tool does not implement OS
sandboxing; use it only for genuinely independent tasks with non-overlapping
external resources. Project identity ambiguities, unresolved dependencies,
missing acceptance or shared writes must be handled before delegation.

For this Pi-Bolt profile, install only the two `megai-factory/` extension files
into its extension directory after a private pre-change receipt/backup and
verify `/delegate` via a fresh read-only RPC probe. Do **not** run the old full
`pi-defaults/install.py`: it still installs retired Headroom/search tooling.
The tool starts only when `/delegate` is invoked and confirmed. Reload the
extension in a user-controlled session when ready; never restart or close an
active user session to enable it. A fresh Paseo workspace is **visible** (not a
background workspace), and the returned IDs let the user open each agent tab.
Paseo's daemon/native Pi provider must already be reachable; the tool does not
start/restart Paseo or modify its provider settings.
