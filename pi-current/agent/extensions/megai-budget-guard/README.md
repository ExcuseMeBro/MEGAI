# MEGAI budget guard

Keeps Pi sessions cheap and short without touching the model choice. It does three things:

1. **Large tool outputs.** A top-level `bash`, `codemode` or `ipython` result over 8,000 characters keeps its first 5,000 and last 2,000 characters. The full text goes to a private file (`0600`, in a `0700` folder), and the result tells the model the path so it can read only the lines it needs. A large result stays in the context and is re-read on every later request, so cutting it once saves tokens many times over. Nested calls made by another tool (for example inside a `codemode` script) are never changed: their output feeds the script, not the model.
2. **Session limits.** Cost, request count and context size are read from the session itself, so they survive `/reload` and resumes. It warns at $5, at 120k context tokens, above 272k tokens (where providers charge about 2× per token), and after 150 requests. Each warning recommends a Factory Flow handoff on the Brokan task and a new session. At $15 it asks once whether to continue up to the next $15; a decline or a 60-second timeout blocks further tool calls in that session until `/budget allow`.
3. **Expensive models.** When the active model costs at least 3× the baseline (`openai/gpt-6.2-sol`) per input or cached token, it says so once. It never switches models.

Measured on this Mac over 7 days (400 sessions, Pi-recorded cost): `gpt-6-astra` was 25% of requests and 78% of cost; the 20 most expensive sessions were 58% of cost; `codemode` returned over 20k characters 1,484 times.

## Modes

| Mode | Logs | Notifies | Caps outputs | Stops at limit |
|---|---|---|---|---|
| `off` | — | — | — | — |
| `observe` (default) | ✓ | — | — | — |
| `warn` | ✓ | ✓ | — | — |
| `enforce` | ✓ | ✓ | ✓ | ✓ |

Set `"mode"` in `config.json`, or override per run with `MEGAI_BUDGET_GUARD=off|observe|warn|enforce` (`0` = off). Recommended path: run `observe` for a week, read `/budget week`, then switch to `enforce`.

## Commands

- `/budget` — this session: cost, requests, context, cost by model, limits, large outputs.
- `/budget week` — last 7 days from the log: how many outputs were (or would have been) capped and roughly how many tokens that keeps out of context, warnings by kind, sessions on an expensive model, finished-session cost.
- `/budget allow [USD]` — raise this session's stop limit (default: one more `stopUsd`).

## Files and privacy

Under `$PI_CODING_AGENT_DIR` (default `~/.pi/agent`) in `budget-guard/`:

- `events.jsonl` — numbers only: time, a hashed session id, event kind, mode, tool name, sizes, cost, tokens, model id. No prompts, outputs, paths or commands. Rotated to `events.1.jsonl` at 2 MB.
- `outputs/<hashed-session>/<tool-call-id>.txt` — the full text of capped outputs. It can contain whatever the command printed, just like the session file; folders older than `retentionDays` (7) are deleted at session start.

Every handler fails open: an error leaves the original result and never blocks a run. All thresholds live in `config.json`; invalid values fall back to the defaults above.

## Install

Copy this folder to `~/.pi/agent/extensions/megai-budget-guard/` and run `/reload` in open Pi sessions. Tests: `node --experimental-strip-types --test pi-current/tests/budget-guard*.test.mjs` (the native test needs Pi 1.5.2 on `PATH`, or `MEGAI_BUDGET_GUARD_TEST_PI`).
