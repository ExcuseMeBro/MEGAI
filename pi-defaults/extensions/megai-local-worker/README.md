# Local durable worker in Pi

Opt-in, human-invoked commands for the separately installed `~/.local/bin/pi-durable`.
The worker uses Pi's native durable Harness with SQLite WAL/FULL on this Mac.
**This is not Vercel `durable-harness`, a Workflow World, a sandbox, or migration of
the current Pi session.** No server/port, boot service, daemon, automatic startup,
model switch, credential copy, cloud deployment or model-callable launch tool.

## Use

Install the standalone runtime first (`pi-durable/README.md`). Install only this
extension with the reviewed `lib/pi_local_worker.py --apply` (set `MEGAI_SOURCE`
to the source checkout); `--check` compares exact owned assets. Use a new Pi session
or explicitly `/reload` yourself; installation never reloads/stops your sessions.

```text
/durable
/durable-init audit
/durable-doctor audit
/durable-run audit architecture-001 Read AGENTS.md and review the architecture. Do not change files.
/durable-status audit
/durable-resume audit
/durable-stop audit
```

Initialization pins the current provider, model, thinking and agent directory,
with **read only** as the sole tool. Doctor checks catalog/auth without a paid model
call. A run/resume requires the same selection; a missing custom/virtual model or
unsupported reasoning level fails, never silently falls back. Change selection
back or initialize a different worker. Installation/init do not copy or edit auth
or settings. Normal native SDK OAuth-token refresh during doctor/run/resume may
update the existing auth credentials, as in the standalone runtime.
Commands that initialize/start/resume/stop require explicit human UI confirmation;
there is no model tool to bypass that dialog. Headless users can deliberately use
the standalone CLI under its own approvals and policy.

Workers are scoped by SHA256 of the canonical working directory plus a short
human name. They do not share the standalone `default` task or other directory's
workers. Private inputs, intent receipts, SQLite state, logs and results live in
`${MEGAI_HOME:-~/.megai}/local-workers/<cwd-hash>/<name>/`. Status returns metadata
and paths, not full transcripts/tool arguments. Read the private `result.json` or
launch log deliberately for the answer. Do not put secrets in prompts or publish
raw logs/state. The model provider receives the explicitly submitted input and
any files read by the worker, as in normal Pi usage.

## Lifecycle and recovery

- A successful launch means **spawn acknowledged**, not admitted, completed, or
  accepted in Plane. Check status and private logs/results. Starting a new process
  does not certify provider access. No live-provider reliability claim is made.
- The request ID is stable per worker. Its content hash and durable launch intent
  are stored before spawning. Same ID/content returns historical metadata, never
  spawns again; same ID/different content fails. Use a new ID only for genuinely
  new work, never to evade an uncertain request. Result paths may describe a prior
  request: verify the `requestId` in the result against the active input/receipt.
- If interrupted between intent and admission (including spawn failure), the
  receipt remains. No automatic retries. Inspect actual state/logs first. Resume
  only an existing active request; an incomplete init or intent without an active
  input requires human reconciliation using the standalone CLI after verifying
  no owner/work was admitted. Never delete locks/state to force a retry.
- The existing supervisor owns a kernel flock also inherited by its worker. Busy
  storage is refused. Process-death restarts are bounded by that supervisor (not
  this bridge); auth/provider/config errors are not automatically retried.
- A worker deliberately survives Pi exit/reload. This extension has **no** shutdown
  handler that signals it. `/durable-stop NAME` has a separate human confirmation
  naming that worker and requests a run-ID-bound cooperative stop, not a PID kill.
  Pending work is retained. No unrelated session/app is stopped.
- Mac off/sleep means no execution. After restart, explicitly inspect and resume.
  Nothing starts at login. Unsafe interruptions remain blocked; this bridge has
  no reconcile/cancel/write-enable command and cannot attest side-effect outcomes.

## Limits and safety

This bridge deliberately does not enable writes, bash, Plane mutations or Git
operations inside the worker. Existing `workflow_checkpoint`, `durable_execute`
and approved knowledge remain separate mechanisms, not permission grants.
For a coding task, use the standalone runtime only after the normal Plane task,
verified task-owned worktree, explicit `--allow-write`, acceptance and reserved
Git delivery checks; this bridge cannot certify that policy or arbitrary tools.

The standalone worker does **not** inherit this session's extensions, MCP tools,
complete ancestor/user instructions, approval hooks, conversation or T3/Paseo
orchestration. It loads its existing runtime preamble and cwd `AGENTS.md` only.
This is why write access cannot be enabled through these commands. Read-only is
not confidentiality isolation: the worker can read paths available to this OS
user, including sensitive files if instructed. Trusted inputs and a suitable
working directory remain essential. Same-user processes/extensions can modify
files; local hashes/markers are consistency checks, not an adversarial sandbox.

Vercel `durable-harness` instead integrates a Workflow World and virtual/per-session
sandbox tools. Running that stack locally is a separate service architecture; it
is not installed or mislabeled here. No guarantee of external exactly-once side
effects, physical power-loss durability, full CLI parity or execution while the
Mac is off.
