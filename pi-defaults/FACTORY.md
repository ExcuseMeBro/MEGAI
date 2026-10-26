# Pellet factory (opt-in)

`/factory all` or `/factory <PELLET_UUID>,<PELLET_UUID> concurrency=2`
works existing project-bound Pellet tasks (1–5 native Paseo Pi agents in any
independent batch). The **only** `/factory` command is the prompt package tracked
at `pi-defaults/pellet-factory/prompts/factory.md` and installed at
`~/.pi/agent/pellet-factory/prompts/factory.md` by the selected package
`./pellet-factory`. `megai-factory/index.ts` exposes the internal model-only
`factory_delegate` tool, **not** a second command; the old Plane-only prompt and
`/delegate` are retired. Plane sync is only through explicit `/splane`. Bare
`/factory` shows usage, without launching agents. The prompt resolves the current
project's UUIDs or identifiers before passing explicit UUIDs to the tool; invalid
selections are rejected as data. A nonempty open/in_progress queue is work, not an
automatic global blocker. Large queues are split into independent batches of at
most five (the underlying tool refuses over 20 IDs at once); never call the tool
with `all` for a 41-task queue. Tasks with existing owned worktrees may instead
require verified serial resumption, never a second writer.

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

For this Pi-Bolt profile, privately back up and update only the two installed
`megai-factory/` extension files and the existing selected `pellet-factory/`
package prompt after verifying ownership and prior hashes. Retire only the exact
legacy global and defaults `/factory` prompt after a verified private backup;
keep the package selection in settings. A fresh read-only RPC probe must show
exactly one `/factory` from `prompt`, with no `/delegate` extension command. Do
**not** run the old full `pi-defaults/install.py`: it still installs retired
Headroom/search tooling. The tool starts only when the prompt explicitly calls it
and the user confirms. Reload an existing Pi session yourself; never restart or
close a user session to enable it. Each fresh Paseo workspace is **visible** (not
background), and its returned IDs identify the agent tab and terminal. Paseo's
daemon/native Pi provider must already be reachable; the tool does not start or
restart Paseo or modify its provider settings.
