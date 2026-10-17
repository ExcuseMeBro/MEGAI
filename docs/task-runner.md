# Explicit fast task flow

`megai task` is a small Python 3.11+ / POSIX CLI, not a Pi extension or a daemon.
It adds no model calls, startup scanning, role routing, package installation, or
background polling. It never invokes the legacy `finish` or `pi-workflow` commands.
Keep the current provider, model and thinking level. This fast path is for a
single repository. Multi-repository umbrella projects must reserve/deliver their
complete repository vector together with the existing queue procedure; the helper
refuses delivery when the configured project root differs from the repository root.

## Operator/agent procedure

First resolve an **existing** Plane project and task, record scope/acceptance there,
and set that task In Progress. The UUIDs below are placeholders, not names. The
helper deliberately has no Plane credentials or status-changing client.
`--plane-current` is a caller attestation of a fresh live check, **not** an API
validation or an authorization obtained from the UUIDs.

```sh
megai task start --root /path/to/repo \
  --project PROJECT_UUID --task TASK_UUID --plane-current \
  --worktree /outside/repo/task-TASK_UUID
# Work only in the returned task worktree. Commit the intended changes there.
megai task verify --root /path/to/repo --task TASK_UUID \
  --check 'YOUR_FOCUSED_TEST_COMMAND' --check 'YOUR_LINT_COMMAND'
megai task ready --root /path/to/repo --task TASK_UUID
# Self-review the COMPLETE base..candidate range and revalidate Plane/authority.
# Confirm both checkouts are idle: no other agent/editor/job owns either writer.
megai task deliver --root /path/to/repo --task TASK_UUID \
  --plane-current --targets-idle --reviewed-sha FULL_VERIFIED_CANDIDATE_SHA
```

`start` creates `task/TASK_UUID` from freshly observed dev in a new native Git
worktree. Local dev must equal fetched/advertised origin dev. It refuses an
existing branch/path/ownership record. A dirty primary does **not** block isolated
implementation or verification; it **does** block delivery. It does not assign,
create, or complete Plane tasks. Never pass an unrelated task's UUID or worktree.

`verify` runs only explicitly supplied shell commands, sequentially, in the clean,
committed owned worktree. Do not put credentials in command text. Output streams to
the terminal; receipts store command, exit code and duration, not raw output.
Select meaningful acceptance checks; `true` is not an acceptance test. A failure,
timeout, source mutation, or moving dev cannot produce a passing receipt. Tests
must leave tracked/untracked files clean (use ignored disposable output paths).
This is not a sandbox: checks need their own isolated ports/databases/resources.
Verification reserves no shared delivery lock.

`ready` is a local read-only check: no fetch, queue database creation, Plane call,
or write. It does not prove online remote freshness or that the queue is free.
It requires the committed candidate, passing receipt, clean/idle Git state and
local/fetched dev pins to agree. The operator still verifies absence of other writers.

`deliver` reuses source-pinned checks instead of running them a second time when
nothing changed. It re-fetches, checks the origin fetch/push URL pair and advertised
SHA, and requires review of the exact verified candidate. It uses the **existing
shared** `megai queue` home, with repository common-dir and remote-dev resources.
Do not override `MEGAI_QUEUE_HOME` per worktree or use the helper to evade a held,
queued, expired or uncertain delivery. Each invocation is explicit; queue claim
never waits/polls. The caller owns live Plane/approval verification; a flag is not
a substitute for doing that work.

While holding a live grant it rechecks pins, runs
`git merge --ff-only --no-overwrite-ignore FULL_SHA` in primary dev, pushes only
`FULL_SHA:refs/heads/dev` to verified origin, fetches again, compares the fetched
and independently advertised head, and checks candidate inclusion in local and
remote dev. Only then does it finish the queue reservation. No bare/force push,
main promotion, PR creation, rebase, reconciliation, reset, stash, automatic
worktree/branch deletion, or changes to other tasks are performed.

## Evidence and blocked delivery

Private task metadata is in `<git-common-dir>/megai-tasks/TASK_UUID/`:

- `intent.json` / `owner.json`: pinned worktree ownership and project/remote identity.
- `verification.json`: source/base pins, checks, exit codes and measured durations.
- `request.json` / `delivery.json`: reservation, exact SHAs, delivery phase and final
  independently observed remote head. Grant tokens stay in the existing queue only.

After verified delivery, attach exact SHAs, affected paths, receipt/check results,
remote URL, local and observed remote tips and timestamp to the **same** Plane task;
then move it In Review, not Done. The helper does not perform tracker acceptance.
All owned resources are intentionally retained; cleanup is a separate guarded step.

Changed dev or divergence requires new source-current checks/review and, where
needed, **explicit** reconciliation. No automatic merge/rebase is attempted.
Unknown ahead commits, dirty/busy primary, mismatched URLs, stale tests, queue
contention, or push/verification failure stop delivery. A failed push can leave
local dev integrated but remote unchanged: keep Plane In Progress and preserve
worktree, branch, journal and queue reservation. Exceptions after grant attempt a
queue hold; an expired/uncertain grant remains blocking even if hold cannot run.
A queued contention remains queued. Interrupted starts/deliveries are deliberately
not replayable; inspect intent/journal and actual Git/queue state first. Reconcile
using the existing queue's evidence/owner-stopped procedure, never by deleting its
journal/database or switching to another integration target.

## Availability and tests

The launcher dispatches to `lib/task_runner.py` (or the refreshed profile's lib).
This source change is **not** a request to reinstall/reset the Pi profile, restore
legacy harness components, overwrite a different installed queue, or change global
agent policies. Activate narrowly only after reviewed delivery, preserving a private
pre-change receipt/backup and verifying the installed queue's compatible API. Before
activation the source CLI can be tested with
`python3 -B /path/to/owned/worktree/lib/task_runner.py --help`.

```sh
python3 -B -m unittest discover -s tests -p task_runner_test.py -v
ruff check lib/task_runner.py tests/task_runner_test.py
bash -n bin/megai
```

Integration tests create disposable local bare remotes and a disposable shared queue;
they never contact project remotes or mutate the production queue. They cover actual
fast-forward/push/inclusion checks and failure/foreign-work preservation paths.
Speed comes from explicit commands, no background services and reusable exact-source
receipts—not a promised model-performance improvement. Measure timings on your machine;
network authentication and test runtime still dominate real delivery.
