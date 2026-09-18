# Jev tool-call gate

`pi-skill/jev/index.ts` — installed as `extensions/megai-jev/index.ts` by
`lib/pi_model_policy.py` — registers a `tool_call` hook next to the `jev` tool.
Every tool call the model emits, built-in or `mcp`/`mcpScript`, gets one Jev `noul`
judgment before it runs: *"this exact call is the right next step for what the
session is working on and should run unchanged"*, answered from the newest user
message on the live branch and the call itself.

- Below 0.5 `should_run` the call is reported (`ctx.ui.notify`, warning) and still
  runs. `JEV_GATE_BLOCK=1` returns `{ block: true, reason }` instead, so the model
  reads why and can narrow or explain the call.
- `JEV_GATE=0` turns the gate off for the session. The `jev` tool itself is never
  gated: a Jev question about the `jev` call would recurse.
- Fail open, no retry: no key, HTTP error, non-JSON, a judgment slower than
  `JEV_GATE_TIMEOUT_MS` (default 5 s) or an agent abort all let the call through
  untouched. A missing or unreadable session only drops the goal from the state.
- It shares `apiKey()` and `jevPost` with the tool and the compaction extension, so
  key resolution, the session-dialog key and the never-echoed-key rule are one path.

Cost per judged call: one Jev request, ~0.8 s p50 added on the tool-call path.

Verify offline through the real loader and the real hook:

```bash
PI_PACKAGE_ROOT=<installed pi-coding-agent> node tests/pi-jev.mjs
```

The gate cases there cover the advisory notify, the block flag, the off switch, the
self skip, the shared session key and the timeout fail-open.
