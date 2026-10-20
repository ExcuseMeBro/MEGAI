# Pi command receipts

A small opt-in T3-inspired reliability layer, not T3's orchestrator and not a new
agent loop. Requires Pi's `ctx.executeTool` API and Node with `node:sqlite` (tested
with Node24.18.0). Uses the existing provider, model, thinking level and session.
No process is launched on load; no hooks, prompt interception or background work.
Existing `megai-durable-workflow` metadata and human knowledge approval stay separate.

## Usage

After scoped installation in `~/.pi/agent/extensions/megai-command-receipts/`,
reload Pi yourself with `/reload` (or use your next newly started session). Copying
files does not change an already loaded extension runtime. Never restart/close a
user session to activate this extension without separate explicit permission.

The model can use `durable_execute` for an **already-authorized**, retry-sensitive
`bash`, `write` or `edit` operation. Supply the verified existing Plane project and
task UUID pair, a stable logical `commandId`, `tool`, and its normal `args` object.
For example, a task's `generate-report-v1` ID must stay the same on reconnect/retry.
Do not substitute a fresh ID to bypass a blocked or failed operation. Ordinary
built-in tools and prompts are unchanged and are NOT deduplicated.

`/receipt-status PROJECT_UUID TASK_UUID COMMAND_ID` reads historical metadata in
the current verified Git repository; it never dispatches or resolves anything.

The UUIDs are caller attestations, not a live Plane query or authorization token.
Check current Plane state, task worktree ownership, permissions and Git/resource
coordination before every new mutation. This tool never reserves a delivery queue,
changes branches, merges, pushes, cleans up, promotes main, or grants approvals.
Normal nested-tool validation, `tool_call`/`tool_result` events and permission checks
still apply. Wrapping a shell command does not make its contents safe or atomic.

## Lifecycle and limits

- A SQLite FULL-synchronous transaction commits `running` **before** dispatch.
- A normal nested tool outcome commits `completed` or `failed` before returning.
  A committed duplicate returns that same historical state without executing.
- The first call returns normal tool content. Duplicate calls return **metadata
  only**, not original output: re-read current authoritative files/artifacts.
  A historical receipt does not prove that files, source, permissions or acceptance
  remain current. It never changes a task's status.
- Same ID with changed arguments, tool, or cwd refuses dispatch. Key order in a
  JSON object is immaterial. Git common-dir + Plane UUID pair define the scope;
  cwd is part of the request fingerprint, so switching worktrees cannot silently
  replay a receipt for another checkout. Independent IDs can proceed independently;
  this does not authorize parallel mutations to shared files/resources.
- Throw/cancellation after reservation marks `uncertain`. A process exit before
  completion leaves `running`. Both refuse retry; no expiry, lease stealing,
  startup replay or automatic reconciliation exists. Reconcile the actual effect
  and authority with the user before a deliberate follow-up operation. Never delete
  receipts, rewrite state or invent a new ID merely to unblock work.
- This is **at-most-one dispatch**, NOT exactly-once side effects. A command may
  partly act and then fail, be aborted, or lose its completion receipt. It can also
  return success despite doing the wrong thing. No provider/model speed or quality
  improvement is claimed. A failed receipt remains failed; fix/retry requires a
  separately considered logical operation, not a blind replay.

## Storage/privacy

Metadata lives under `${MEGAI_HOME:-~/.megai}/command-receipts/<scope-hash>/` in a
private SQLite database. Only command ID, request hash, lifecycle state, random
owner ID, session ID and timestamps persist. No raw prompt, arguments, tool output
or exception text is stored in this database. Command IDs must not contain secrets.
The ordinary Pi transcript can still record tool input/output, including bounded
nested call arguments; this extension does not redact normal session logs.
Do not send secrets through it. Arguments are limited to64KiB of canonical JSON.

Owned private directories/files are required. Symlinks, hardlinked database files,
public modes, unknown schema, invalid records and persistence failures block work.
There is no migration/reset fallback. This is a cooperative local reliability
mechanism, not a security boundary against another process running as the same user
and able to alter/delete the database. It cannot guard operations bypassing it.

## Verification

```sh
node --test tests/pi-command-receipts-store.test.mjs
node --test tests/pi-command-receipts-extension.test.mjs
```

Tests use disposable Git scopes, SQLite, real filesystem effects and the installed
Pi loader/SDK/nested-tool validation and permission pipeline. The SDK tests supply
an assistant-message fixture through the authoritative SessionManager; they make
no model/provider call. An exited Node worker tests the dispatch/completion gap;
no user Pi/Paseo session is signalled or terminated. This is not a full end-to-end
provider interruption test or an implementation of T3 child/root execution graphs.
