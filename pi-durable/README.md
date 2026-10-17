# Standalone Pi Durable

An **opt-in separate coding runtime**, based on pinned `@earendil-works/pi-durable@1.1.0`.
It runs in a terminal without an orchestration app, daemon, workspace registry or its configuration.
The existing `pi` command, Pi sessions/extensions, auth configuration and model defaults are not replaced.
This is not a setting that makes existing coding-agent sessions crash-resumable.

## Install

Requires macOS/Linux, Python 3 with `fcntl`, npm and **Node.js 24+** (`node:sqlite`).
From this source directory:

```sh
python3 -B install.py              # preflight only
python3 -B install.py --apply      # pinned npm ci --ignore-scripts; scoped installation
pi-durable --help
```

Installs a private, content-addressed runtime under `~/.megai/pi-durable/runtime/`
and one owned launcher at `~/.local/bin/pi-durable`. Add `~/.local/bin` to your PATH
if necessary. `--home` / `--bin-dir` support alternative install locations. Runtime
versions and private upgrade backups are retained; no automatic cleanup of data.
The destination command is published atomically without clobbering an existing
file. Its dispatcher remains unchanged on upgrades; only the private runtime
receipt switches versions. Installers targeting the same bin directory coordinate
through a destination lock, even with different installation homes.
The installer refuses changed/custom launchers, symlinks and managed-source drift.
An interrupted publication may require manual reconciliation; never delete unknown
files or retry an uncertain install blindly. It starts no server or background job.

## Start a task

```sh
TASK="$HOME/.megai/pi-durable/tasks/my-task"
pi-durable init --task "$TASK" --cwd "$PWD" \
  --provider openai-codex --model gpt-6.1-sol --thinking medium
pi-durable doctor --task "$TASK"
umask 077
printf '%s\n' 'Inspect the project and explain the failing test.' > /tmp/task-prompt.txt
pi-durable run --task "$TASK" --prompt-file /tmp/task-prompt.txt --request-id inspection-1
```

`init` is read-only by default: only the file-reading tool is offered. To permit
`write`, `edit` and arbitrary `bash` commands, create the task with `--allow-write`.
This is the human's grant of host write/shell access for that task, **not a sandbox**.
Do not enable it for untrusted prompts. The task cwd is not a filesystem jail.
The cwd's `AGENTS.md` is loaded (bounded to 64 KiB); consult any nested repository
instructions when entering subdirectories. Full Pi skill/extension, MCP, Headroom
and discovery parity is not implied by these four basic tools.

Config is private, per-task `config.json`, never a global app config. `init` defaults
to the current Pi model/thinking environment when present, otherwise the explicit
defaults shown above. Model, thinking, cwd, write policy and auth location become
bound to the stored conversation on first open. Changes then fail closed: create a
new task instead of changing a running task's policy. No model/provider fallback.
Unsupported thinking levels and unavailable catalog models are errors, not silent
clamps. `doctor` checks local model catalog/auth configuration, **not a live request**.

The optional `--agent-dir` defaults to `PI_CODING_AGENT_DIR` or `~/.pi/agent`.
The SDK uses that directory's native `auth.json`, `models.json` and cached model
catalog; it does not load other app state or extensions. An independent Pi auth
location can be supplied; environment API keys also use native provider behavior.
Normal SDK OAuth-token refresh may update native auth credentials; installation
does not change credentials or default model settings. Never put secrets in argv.

## Recovery, status and stop

```sh
pi-durable status --task "$TASK"
pi-durable resume --task "$TASK"
pi-durable stop --task "$TASK"
```

`run` is foreground and supervised. A request is saved before admission; `requestId`
deduplicates resubmission. Reusing an ID with different prompt content is rejected.
Successful inputs clear the active request; their transcript and result remain.
After a crash, `resume` continues the same active request. A failed or stopped
request is retained for inspection, not silently replaced by a new request.

The supervisor restarts an unexpectedly killed worker at most twice (configurable
`--max-restarts 0..3`). Auth/provider errors, validation errors and ordinary storage
failures exit immediately, without provider switching or restart loops. After a host
reboot or loss of the supervisor **and** worker, launch `resume` explicitly: no
boot-time service or always-on daemon is installed. Persistent state is not a
promise that a powered-off machine keeps executing.

A kernel `flock` gives one process tree exclusive ownership per task storage. The
worker inherits that lock: a supervisor crash cannot admit a second writer while
its worker is still alive. No lock stealing or timeout-based ownership guess.
`status` can read private committed progress while owned; an offline status opens
storage with scheduling paused. `stop` requests graceful close, retaining pending
work. Some code may delay close while responding to cancellation; a stop request
is not proof of stopped execution. Inspect `status` before resuming/reconciling.

### Interrupted side effects

Only `read` is replay-safe. `bash`, `write` and `edit` are unsafe, even if one bash
command happens to be a search. Intent is committed before execution. An unsafe
interrupted call blocks **all automatic continuation before the scheduler starts**.
No model gets to silently recreate that operation as its recovery strategy.

Inspect the reported task/call IDs, arguments and actual files/services/processes.
Once all effects are known and the old execution has stopped, use a **human terminal**:

```sh
pi-durable reconcile --task "$TASK" --note 'Confirmed the file was written once; do not repeat it.'
pi-durable resume --task "$TASK"
```

The note and exact interrupted task identities are recorded atomically. The original
unsafe call produces an interrupted result rather than re-executing. Reconciliation
is an explicit assertion about real outcomes, not an automatic safety proof. A model
can still issue new actions after continuation, so review the scope and your note.
No exactly-once guarantee is claimed for external APIs, payments, messages or shell
commands. Those require their own idempotency keys and approvals.

To abandon a failed/stopped request rather than retry it:

```sh
pi-durable cancel --task "$TASK" --note 'Inspected failure; abandon this input and retain its history.'
```

Cancellation aborts pending task work and archives the active input without removing
its transcript. Unsafe interruptions still require reconciliation first. `stop`
retains pending work; `cancel` deliberately abandons it. Use a **new** request ID
for an intentionally new attempt after a provider failure.

## Storage and limitations

SQLite uses WAL and `synchronous=FULL`, verified on every open, rather than upstream's
NORMAL default. Private directories/files, bounded JSON records, atomic rename,
file/directory fsync and config fingerprints protect local consistency. They do not
protect against malicious processes running as the same user, broken hardware,
unreliable/network filesystems or disk exhaustion. Keep independent backups; never
copy only the SQLite main file from an active WAL database.

The upstream API/storage format is **experimental**. Dependencies are locked; an
upgrade requires fresh recovery tests and a backup/migration plan. No data migration,
unlimited model memory, unlimited retry budget, multi-host shared storage, full Pi
TUI, automatic imported sessions or compatibility with coding-agent extensions is
claimed. Native model context limits and compaction costs remain.

`MEGAI_DURABLE_TESTING=1` plus `MEGAI_DURABLE_TEST_MODULE` enables an internal test
fixture in the source launcher. It is never set by installation; do not use it for
real tasks. Like all loaded code it has host permissions, not a security boundary.

## Verification

```sh
node --test pi-durable/test/runtime.test.mjs
python3 -B pi-durable/test/install_test.py
ruff check --no-fix --no-fix-only --force-exclude --no-cache pi-durable
```

Run these from the repository root after `npm ci --ignore-scripts` in `pi-durable`.
Tests use a faux provider with the **real pinned durable Harness, SQLite, launcher,
process kills, locks and supervisor** in disposable local directories. They are not
live-provider certification or a simulated power-loss guarantee. No browser needed.
