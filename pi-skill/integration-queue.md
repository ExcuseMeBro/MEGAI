# Integration queue — parent operating contract

Use `megai queue` when multiple tasks may integrate into the same repository or
share an explicitly named runtime resource. Installed copy:
`$MEGAI_HOME/pi-skill/integration-queue.md`. Run `megai queue --help` for flags.

## Boundaries

- Plane remains the task/acceptance/status authority. The SQLite queue is a local
  resource-reservation journal, not a second task board. Every request carries the
  existing Plane pair and existing Paseo project identity.
- Workspace isolation belongs to `agent-worktree-lifecycle`: one canonical Paseo
  project, a managed worktree for each affected Git repo/task, no child-project
  registration. Queue planning resolves linked worktrees to their primary repo.
- The queue NEVER merges, rebases, switches branches, pushes, starts an agent or
  daemon, installs hooks, calls Plane, or approves deployment. A grant does not
  prove acceptance or authorize main promotion. Complete the independent,
  source-current acceptance gate before the separately agreed integration.
- Reservations are cooperative, not a filesystem sandbox. All integrating parents
  on this machine must use the same queue and respect ownership. Unmanaged Git
  commands, other machines, running apps and ignored build outputs are not fenced
  by SQLite. Coordinate those writers explicitly; use a distributed coordinator
  rather than placing this SQLite file on a network filesystem.

## Plan and join once

Keep request/grant/evidence files private and outside source roots. Set a restrictive
umask before redirecting JSON. Use one stable operation ID such as
`PLANE_WORK_ITEM_UUID:integration-1`; retries reuse it. Different operations use
new IDs. The example variables are placeholders resolved by the parent.

```bash
umask 077
megai queue plan --root "$PROJECT_ROOT" --id "$OP_ID" \
  --plane-project "$PLANE_PROJECT_UUID" --plane-item "$PLANE_ITEM_UUID" \
  --repo backend task/login --repo frontend task/login > "$PRIVATE/request.json"
megai queue enqueue --request "$PRIVATE/request.json"
megai queue status --id "$OP_ID"
```

For a monorepo use `--repo . task/login`. Paths are relative to `--root` or absolute.
By default the target is the **current branch in each primary checkout**, not an
assumed dev branch. For an agreed non-checked-out target use `--target-branch pi`
(or another explicit branch name, applied to every selected repo). The target ref
must already exist and must not be checked out in another worktree. Verify the
agreed target before planning; the CLI pins target branch/head/candidate plus the
primary checkout branch/head and Git common-directory identity. Ref-only delivery
checks the target ref while requiring the unrelated primary checkout to remain
unchanged. It never switches branches or performs the ref update/push itself;
those remain explicit parent-owned CAS/delivery operations with remote verification.
Planning is read-only and needs a unique existing Paseo project; umbrella folders
need no Git. Use separate operations if repos require different target branch names.

Optional `--after OP_ID` references already enqueued integration operations, not
arbitrary Plane IDs. This earlier-only rule prevents dependency cycles. Only a
`completed` integration satisfies dependents; failed/cancelled dependencies remain
visible until the parent cancels/replans the dependent work.

Optional `--resource external:namespace:name` reserves an additional shared resource.
Use exactly the same name for the same port/DB/test environment across projects;
never put credentials in names. Allocate separate runtime ports/DB schemas where
possible. This flag reserves a name; it does not provision or isolate that resource.

The default journal is `~/.megai/queue/queue.sqlite3`, private and shared across
projects. `--home` / `MEGAI_QUEUE_HOME` is for an explicitly coordinated location
or disposable tests, never a per-worktree lock directory. Protect its backups and
keep the full directory; do not delete/reset queue state to escape an active grant.

## Wait without losing position

```bash
megai queue claim --id "$OP_ID" --owner "$EXECUTOR_INSTANCE_ID" \
  --lease-seconds 120 --wait-seconds 60 > "$PRIVATE/grant.json"
```

An executor identity names one parent execution instance, not a generic shared
`worker` name. A successful claim returns a private token. An identical retry by
that owner returns its current token; another owner cannot take it. Keep grant
files private, including shell arguments/process visibility on a shared machine.

- `0`: command succeeded (a claim includes its token).
- `2`: waiting/BLOCKED; inspect JSON `wait_reason` or `reason`. Ordinary CLI argument
  errors also use exit 2 on stderr. Do not interpret exit zero as acceptance PASS.
- `resource:ID`: active overlapping grant; `fifo:ID`: earlier eligible overlapping
  request; `dependency:ID:STATE`: unmet dependency; `reconcile:ID`: uncertain owner.
- All repository resources are reserved in one SQLite transaction: no partial lock
  acquisition or hold-and-wait deadlock. Ready conflicting requests follow FIFO;
  unrelated resources progress even while another request waits. An unresolved
  dependency does not reserve its dependent's resources ahead of ready work.
- Bounded wait sleeps between local checks, releases the SQLite transaction while
  waiting and retains the original queue sequence. It starts no background service.
  When it expires, checkpoint and return to the parent; later claim reuses the same
  ID. Do not launch agents to poll, repeatedly enqueue, or drain unrelated work.

Claim rechecks the pinned target vector and clean checkout. If another integration
advanced the base while waiting, perform required rebase/test/review in the task's
isolated checkout. Generate a new plan with the **same operation ID**, then:

```bash
megai queue refresh --request "$PRIVATE/refreshed.json" --evidence "$PRIVATE/review.txt"
```

Refresh is queued-only, preserves sequence/target and checkout branches/resource set/dependencies, and
records the actual evidence file hash. It is an attestation, not a replacement for
acceptance verification. Resource-set changes need cancellation and a new operation.

## Integrate only with a live grant

The parent verifies current acceptance, agreed target and other agents/terminals,
then uses the existing approved Git delivery procedure. The queue does not execute
it. Keep a lease alive with `heartbeat --id --owner --token --lease-seconds`; choose
bounded operations and renew before expiry. Never interrupt a live mutation merely
because a lease or five-minute checkpoint elapsed.

`finish --id --owner --token --outcome completed` releases resources only when
**every** target ref is at its exact candidate commit and each primary checkout is
clean on its pinned branch (and unchanged HEAD for ref-only integration).
This records integration, not tests or Plane Done. `--outcome failed` releases only
if every clean target still has its original HEAD. Check `status` after an uncertain
finish response instead of replaying any Git mutation. A queued request can use
`cancel --id --reason`; active cancellation is refused.

## Crash, uncertainty and partial multi-repo delivery

Expiry retains all resources. No automatic owner stealing, model retry, timeout
rollback or force reset. `hold --id --owner --token --reason` explicitly marks an
uncertain live grant. Preserve logs, source work and all target outcomes.

1. Inspect the old Pi agent and its terminals/processes. Confirm the old executor
   and its in-flight Git commands have actually stopped. A stale timestamp alone
   is insufficient. Record this and observed per-repo heads in a private evidence
   file. Reconciliation's `--owner-stopped` is the parent's attestation, not process
   detection or an OS fencing guarantee.
2. Use `reconcile --id --owner-stopped --evidence FILE --outcome ...`:
   - `retry`: every target unchanged; return to the same FIFO position, invalidate
     old token, and claim again.
   - `failed`: every target unchanged; release with a failed integration result.
   - `completed`: every target at its exact candidate; record observed completion
     without replaying already-completed mutations.
   - `resume --owner NEW_EXECUTOR --lease-seconds 120`: each target must be at its
     original or candidate HEAD. Retain the entire bundle, rotate token and return
     `remaining_repositories`. Recheck acceptance/authorization and operate **only**
     on those remaining targets, then finish the full candidate vector.
3. Any unknown head, dirty target, changed identity/branch or unresolved Git operation
   remains BLOCKED. Diagnose it under retained ownership; do not silently reset,
   narrow the resource set or infer that an uncertain external operation failed.

Multi-repository delivery is not atomic: backend may have advanced before frontend.
Plan backwards-compatible interfaces or an explicitly approved rollout strategy.
After verified delivery, the parent records evidence in Plane In Review and follows
normal released-workspace cleanup. Active/unmerged work and backups are retained.
