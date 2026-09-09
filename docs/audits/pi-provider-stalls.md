# Pi provider stall audit — 2026-09-09

## Incident evidence

The affected ADAM parent (`458814d8…`) had an active turn beginning at
08:46:18Z. Raw native Pi JSONL, rather than the agent's narrative, establishes:

| Event (UTC) | Evidence |
| --- | --- |
| 09:52:02.477 | Native `read` tool completed |
| 10:40:39.421 | Assistant/provider error: `terminated` (2916.944s gap) |
| 10:55:31.498 | Second assistant/provider error: `terminated` (892.077s gap) |
| 10:56:24.461 | Plane MCP call actually started |
| 10:56:30.465 | Plane MCP call returned (6.004s) |

The two provider intervals total 3809.021s (63.48 minutes). The agent's claim
that Plane took 64 minutes was incorrect; audit coordination asked it to correct
that attribution, and its subsequent activity includes the correction. The
underlying remote cause of `terminated` is not established by these local logs.

Paseo MCP agent listing defaults to the current cwd: a MEGAI-only list did not
show ADAM. Global CLI inventory distinguished running turns from old idle Pi
processes. Another running project had just received a new user message, not a
two-hour stall. No blanket kill, archive, daemon restart or config reset occurred.
ADAM resumed code/test activity and its saved work was not interrupted.

## Reproduction and remedy

Installed Pi native Codex SSE transport accepts `timeoutMs`, but uses it for
response headers. The body reader waits until completion or explicit abort.
A no-network synthetic native-stream test with `timeoutMs=20` and a body that
never completes required a separate 150ms safety abort; the assertion failed.
Thus simply changing timeout settings would not establish a complete fix.

The separate `megai-provider-guard` extension bounds the model request plus its
automatic retries to 180 seconds, using Pi's native abort. It starts no startup
daemon or provider request. It never changes model/provider/thinking/auth,
payloads, retry settings, tool arguments, or native tool results. Tools are
excluded, including nested provider work while parallel tools are active.
Successful assistant responses, settled sessions, compaction completion and
shutdown clean up timers. Native retries retain the original request budget.

`MEGAI_PROVIDER_TIMEOUT_MS=0` explicitly disables the guard; a positive integer
sets a different budget. Invalid values fall back to 180000ms. A timeout is not
a success, task completion, or automatic permission to replay work or switch
models. The parent must reconcile saved evidence and choose the next bounded
step. This does not guarantee completion of whole tasks within three minutes,
and cannot preempt a blocked JavaScript event loop or a provider ignoring abort.

## Verification and activation

Offline commands (explicit installed Pi package; no provider calls):

```sh
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-provider-guard.mjs
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-provider-session.mjs
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-model-guard.mjs
python3 tests/pi_model_policy.py
ruff check --no-fix --no-fix-only --force-exclude --no-cache -- lib/pi_model_policy.py tests/pi_model_policy.py
git diff --check
```

The provider test exercises the actual Pi loader and native Codex SSE reader,
plus parallel/nested tool protection, retry budget retention, cleanup and opt-out.
The policy suite covers receipt-owned installation/removal, idempotency, custom
asset refusal, settings/auth preservation, and related distribution behavior.

A fresh Pi/Sol independent reviewer approved the safety design and identified
that the initial fixture mocked `ctx.abort`. The additional full AgentSession
test closes that gap: real extension bindings, native SSE abort, zero retries
after abort, cancellation during actual retry backoff, and preserved original
`terminated` history all pass. Only auth preflight and fetch are fixture stubs;
no live credentials or remote model calls are used. The policy suite passed 63
tests; original model-guard and task-changed Python Ruff checks also passed.
The reviewer additionally identified direct SDK disposal invalidating the context
without a shutdown event. The fix catches stale callbacks, with both synthetic
and full-session disposal regressions passing. Final independent verdict:
APPROVED, no blocking findings.

Receipt-owned installation uses `lib/pi_model_policy.py`; global extension
auto-discovery needs no settings-array changes. Existing resource opt-outs win.
Installing files does not hot-patch running Pi instances. Reload/reopen only at
an idle boundary; retain native sessions and reconcile uncertain mutations first.
Local installation was completed through the existing receipt transaction;
preflight asserted that only the new provider-guard asset changed (plus its
ownership receipt). Settings, auth, models and AGENTS bytes remained unchanged.
Backup: `~/.megai/backups/slim-wiring-sftx2wy6`. The actual global Pi resource
loader then selected the installed extension and its offline regression passed:

```sh
MEGAI_PROVIDER_GUARD_AGENT_DIR="$HOME/.pi/agent" \
  PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-provider-guard.mjs
```

This proves new-runtime loading, not activation in existing agent processes.
Main promotion requires separate explicit user approval.
