# Task resource lifecycle (Pi, Codex and Claude)

Use `python3 scripts/task_resources.py` (installed as
`~/.local/bin/megai-task-resources`) synchronously during task delivery, **not** a
Git hook, background janitor or a global Docker prune. Install or refresh the
helper and the shared policy block in one step:

```sh
python3 scripts/install_task_resources.py
```

It copies the helper to `~/.local/bin`, makes it executable, and replaces the
`megai:task-resources` block in `pi-defaults/AGENTS.md`, `~/.pi/agent/AGENTS.md`,
`~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md` with the exact bytes of
`docs/task-resources-policy.md`; it is idempotent and refuses a policy file whose
markers are missing. Instructions are shared in
`docs/task-resources-policy.md`. They apply to new task resources; existing
unlabelled resources are deliberately not adopted or deleted.

## Allocate, verify delivery, release

1. In the task worktree, choose a unique slug, e.g. `megai-835-session-a`.
   Obtain the labels:
   ```sh
   megai-task-resources labels --repo "$PWD" --task megai-835-session-a
   ```
2. Put **all three returned labels** on disposable task containers, images,
   networks and volumes at creation. `io.megai.repo` is a hash of the resolved Git
   common directory (shared by worktrees), `io.megai.task` is the unique slug,
   `io.megai.disposable=true` is explicit permission to delete after delivery.
   Do not reuse slugs for concurrent tasks or label persistent DB data disposable.
   Use separate Compose project names per task. Compose's own project labels are
   not sufficient, and service labels do not propagate to volumes/networks/images.
3. For Compose, add the returned mapping to each service's `labels`, each
   disposable top-level volume/network's `labels`, and built image `build.labels`.
   Use `${TASK_REPO}`, `${TASK_ID}` interpolation, passing values explicitly:
   ```yaml
   services:
     redis:
       image: redis:7-alpine
       labels: &task_labels
         io.megai.repo: ${TASK_REPO:?required}
         io.megai.task: ${TASK_ID:?required}
         io.megai.disposable: "true"
       mem_limit: 256m
       cpus: 1
       volumes: ["cache:/data"]
   volumes:
     cache:
       labels: *task_labels
   networks:
     default:
       labels: *task_labels
   ```
   Shared Redis/Postgres/RustFS data volumes must be **external**, without the
   disposable label. Cleanup does not remove bind mounts or implicit anonymous
   volumes. Prefer labelled named volumes, `tmpfs` for ephemeral data, and `--rm`
   for short-lived containers. Never use production data for disposable tests.
4. Finish checks, commit, merge/push dev, verify the full delivered SHA remotely.
   Stop task test runners that could recreate resources, then while still in the
   clean `task/*` worktree (before removing it):
   ```sh
   megai-task-resources cleanup --repo "$PWD" --task megai-835-session-a \
     --context kiri --commit "$(git rev-parse HEAD)"
   # Inspect preview; same command plus --apply performs cleanup.
   megai-task-resources cleanup --repo "$PWD" --task megai-835-session-a \
     --context kiri --commit "$(git rev-parse HEAD)" --apply
   ```
   The helper fetches `dev` explicitly and verifies ancestry even for preview.
   Failure means report and fix the cause, not bypass the gate. Deletions are
   sequential, not transactional: an interrupted run can have partial effects;
   rerun after reconciling. No force flags: in-use resources cause refusal.
5. Remove the merged task worktree/branch and attach cleanup evidence to the task.
   Keep durable dev services, unrelated tasks, persistent volumes and shared
   caches. Never run `docker system prune -a --volumes`, wildcard volume removal,
   or stop Java/VM processes globally as a delivery step.

## Cache and process budgets

- Shared BuildKit: target 8 GiB cache, idle stop 300 seconds on this Mac. Kiri
  `POST /kiri/builder` stores `{"cache_gb":8,"idle_secs":300}`; read it back with
  `GET /kiri/builder`. The setting applies at the builder's **next start**. Do not
  restart a builder during someone else's build. GC is a target, not a hard quota;
  live/referenced cache can exceed it. Kiri's Docker `system df` may report zero
  build-cache sizes or `-1` volume sizes: these are not proof of empty storage.
- For task-private BuildKit, use a dedicated builder and explicitly labelled
  disposable state volume. Delete only after that task finishes. A shared cache
  cannot safely be pruned merely because one task merged.
- Bound container memory/CPU and log size using supported engine options. Confirm
  the engine actually enforces them. Avoid a daemon/build worker per command.
- For isolated Gradle acceptance jobs prefer `--no-daemon --max-workers=2`,
  project-supported `-Dorg.gradle.jvmargs='-Xmx2g -XX:MaxMetaspaceSize=512m'`, and
  `-Pkotlin.compiler.execution.strategy=in-process` when compatible. Do not
  rewrite global JVM settings or stop another project's daemon. These are starting
  budgets, not universal limits; raise only when a measured build needs it.
- No automatic home/cache purge. Retain dependency caches; remove only proven
  task-owned output after verification. Preserve uncommitted work before cleanup.

## Kiri disk meaning and safety

On this Mac, `~/Library/Application Support/kiri/vm/data.img` is a sparse
**64 GiB (68,719,476,736 byte) virtual disk already**. Its logical size is the
VM data disk ceiling; actual allocated host blocks are a different number. Never
truncate/shrink a mounted filesystem, delete this disk, or reset Kiri to reduce
storage. No restart/migration is needed to retain the current 64 GiB ceiling.

Kiri also stores **host-side** images/blobs under `~/Library/Application Support/kiri`;
the VM disk ceiling is **not** a 64 GB quota for the entire application. Decimal
64 GB is also not the same as 64 GiB. A hard aggregate quota needs separately
planned storage migration/quota support; this helper does not pretend to provide
one. Deleting container data may free guest space without immediately returning
host disk blocks. Do not promise automatic compaction or issue unsupported TRIM.

Check without modifying storage:
```sh
stat -f '%z bytes logical, %b allocated 512-byte blocks' \
  "$HOME/Library/Application Support/kiri/vm/data.img"
du -sh "$HOME/Library/Application Support/kiri"
docker --context kiri system df
```

## Trust boundary

This is a local operator tool, not a tenant/security sandbox. Anyone controlling
Git configuration, the Docker socket, labels or the executable has local deletion
power already. It validates identifiers, pins an explicit local Unix socket,
ignores inherited Docker endpoint overrides, re-inspects labels before removal,
and refuses stale/unmerged commits and dirty worktrees. Remote/TCP contexts,
unlabelled resources, image force-removal and global prune are unsupported.
Kiri currently omits image labels from its Docker list/inspect API. On the exact
local `~/.kiri/run/docker.sock` endpoint only, the helper reads the image's raw
config from the standard host store, verifies its SHA256 and 1 MiB size bound,
and checks the same labels. Missing/changed/custom stores fail closed, rather
than inferring ownership from image names. No store files are written.
Concurrent writers using the same task slug must be quiesced before cleanup;
Docker has no transactional label-and-delete primitive. Persist this tool's stdout
(resource IDs only) as the cleanup receipt; do not log container environments.
Process-level reclamation reads the OS process table and signals only by numeric
pid with `SIGTERM`, never by name pattern or shell string, and re-reads the table
immediately before signalling, so a recycled pid is refused by the same age,
client and command checks; nothing is ever forced with `SIGKILL` and no process
the tool did not classify is signalled.

## Sweeping leftovers, temp clusters and caches

Per-task `cleanup` only knows one slug. Older or abandoned leftovers are handled
by two read-only-by-default commands; both print JSON lines and mutate nothing
without `--apply`.

```sh
# Labelled groups of finished tasks + unreferenced anonymous volumes
~/.local/bin/megai-task-resources sweep --context kiri --anonymous-volumes
# Orphaned PostgreSQL servers started from a temp directory
~/.local/bin/megai-task-resources sweep --context kiri --temp-clusters
# Regenerable Gradle version caches and wrapper distributions nobody references
~/.local/bin/megai-task-resources caches
```

Rules the sweep enforces:

- A group is touched only when its `io.megai.repo` hash re-computes from a
  recorded common dir (`labels` records it in
  `~/.local/state/megai-task-resources/registry.json`, mode 0600) or from an
  explicit `--repo-dir`, and the task's `refs/heads/task/<slug>` plus any worktree
  using it are gone. Unresolvable or active tasks are reported as `skip`.
- `--min-age-hours` (default 24) protects freshly created resources.
- Anonymous volumes are only the 64-hex unnamed ones no container mounts and
  that carry no `io.megai.*` label. Named, labelled and mounted volumes stay.
- Temp clusters must be `ppid 1`, inside `/tmp`, `/private/tmp` or `$TMPDIR`,
  older than the gate; the helper sends `SIGTERM`, waits a bounded time, and
  removes the data dir only if the server actually exited.
- `caches` removes only `~/.gradle/caches/<version>` directories and
  `~/.gradle/wrapper/dists/gradle-<version>-*` downloads that no
  `gradle-wrapper.properties` under `--projects-root` (default `~/PROJECTS`)
  references. Shared dependency caches (`modules-2`, `jars-9`, `journal-1`) are
  retained; project build output and `node_modules` are never touched.

Kiri's `docker system df` can report tiny volume/build-cache sizes while the host
disk is mostly the VM image and host-side caches. Measure with `du` and
`stat -f %b` before promising reclaimed space.

## Memory pressure and idle servers

Disk leftovers and RAM exhaustion have different owners: on this Mac the disk is
typically the Kiri VM image plus Gradle caches, while memory pressure comes from
live emulators, JVM heaps, Docker VMs and abandoned dev servers. `mem` is a
read-only diagnostic that mutates nothing:

```sh
# Swap, compressor, top processes by footprint, oversized -Xmx, idle servers
~/.local/bin/megai-task-resources mem --top 10

# Preview (or stop with --apply) dev servers idle past the gate with no clients
~/.local/bin/megai-task-resources sweep --context kiri --idle-servers
```

Reading the report:

- `swap.used_bytes` above half of `swap.total_bytes`, or `compressor_bytes`
  above a fifth of RAM, means the machine is already oversubscribed: defer heavy
  work instead of starting another build, emulator or container stack.
- `top`/`heavy` report both `rss` and `footprint`; `footprint` comes from a
  best-effort `top -l 2` sample and includes compressed pages, so an emulator can
  show a small RSS and a multi-gigabyte footprint. `footprint_available: false`
  means the sample failed and the numbers are RSS-only lower bounds.
- `oversized-jvm-heap` warns about any `-Xmx` at or above 6 GiB; `heavy-emulator`
  warns about a software-GPU emulator holding 4 GiB or more; `swap-pressure` and
  `compressor-pressure` are host-level.
- `idle_servers` lists of age-gate dev servers (`craco`, `next dev`, `vite`,
  `webpack serve`, `react-scripts`) with zero established TCP clients.
  `sweep --idle-servers --apply` sends `SIGTERM` to the process and its
  descendants, waits a bounded time, and reports `still-running` rather than
  forcing. Emulators, IDEs, Docker VMs and JVM daemons are never auto-stopped:
  they hold another session's state and are only reported.
