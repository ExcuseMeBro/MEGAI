# Read-only Pi usage report

`lib/pi_usage_report.py` aggregates local Pi session logs into the numbers that
actually drive a session's cost: prompt tokens per assistant turn, turns per
session, reported cost per model, tool-call batching and the replay amplification
of retained tool output. It is stdlib-only, reads sessions read-only, makes no
provider request and prints no transcript content, message text, session file path
or working directory.

`--by-project` is the only mode that prints a local label (the session directory
name). It is off by default and can contain local path text.

## Usage

```bash
megai report --text                       # human table (read-only)
megai report                              # JSON
megai report --days 7 --by-project
megai report --limit 3                    # trim the model ordering
megai report --since 2026-09-01T00:00:00Z --until 2026-09-08T00:00:00Z
```

`megai report` resolves the installed script (`~/.megai/lib`, falling back to
`~/.megai/pi-profile/lib`). From a checkout, run
`python3 lib/pi_usage_report.py` directly.

`--agent-dir` defaults to `PI_CODING_AGENT_DIR` or `~/.pi/agent`. `--days` filters
by session file modification time; `--since`/`--until` filter individual entries by
their recorded timestamp. `--limit` trims the reported model ordering only.

## What each number is, and is not

- **`prompt_tokens` / `context_tokens_per_turn`** are `input + cacheRead` from the
  session's own usage objects. They are the size of what the model is sent, not
  unique new content: `cacheRead` counts a cache lookup that is re-sent per request.
- **`reported_cost`** is the cost estimate carried in the session log. It is **not**
  a bill. Providers report it inconsistently, and one model's reported cost is not
  comparable with another's as a price list.
- **`reported_cost_per_turn`** is the only fair per-model comparison the log
  supports, and it is derived, not provider-supplied.
- **`missing_usage` / `cost_missing`** count assistant messages whose usage or cost
  object was absent. Missing is reported as missing, never as zero; `totalTokens`
  then sums only the observed parts.
- **`summarization`** reports compaction and branch-summary usage separately. It is
  real provider work, so it is never hidden inside the model totals, and it is what
  a smaller context budget trades against.
- **`replay_tokens_estimate`** is an **estimate**: it assumes a retained tool result
  is re-sent on every later assistant request in that session and ignores compaction.
  It is an upper bound, not a measured re-send count, and the basis (`chars/4`) is
  printed with it so the assumption is visible.

No percentage saving, latency or quality conclusion is derived from these totals.

## Observed baseline (local, 2026-09-15)

One local 14-day window, 87 sessions matched of 111 files scanned, produced by:

```bash
python3 lib/pi_usage_report.py --text
```

| Model | Turns | Prompt tokens/turn | Reported $/turn | Reported $ |
| --- | --- | --- | --- | --- |
| `openai-codex/gpt-6-astra` | 2222 | 91,662 | 0.1474 | 327.54 |
| `deepseek/deepseek-flash` | 1570 | 116,890 | 0.0022 | 3.46 |
| `openai-codex/gpt-5.6-luna` | 253 | 82,221 | 0.0026 | 0.66 |
| `openai-codex/gpt-5.3-codex-spark` | 2 | - | 0.0000 | 0.00 |

Totals for the same window: 4047 assistant turns, 5718 tool calls, 4 compactions,
68.5% of turns issued exactly one tool call, summarization work of 4 calls
(357,777 input tokens, 16,926 output tokens, reported $4.42). Estimated replay of
retained tool output: `read` 116.4M and `bash` 107.4M tokens (upper bound).

Reading of that window, and its limits:

- Prompt re-sends, not output, are the cost. `cacheRead` is ~96% of reported
  tokens, so the multiplier is *turns x prompt size*.
- The displayed per-turn cost ratio between models is a ratio of **reported**
  estimates from different providers. It is a signal for routing review, not a
  price comparison and not a billing claim.
- The largest single-tool-call ratio is the cheapest available lever: batching
  independent calls into one turn removes whole round trips.
- The replay figures are an upper bound because compaction is not modelled; a
  session that compacts re-sends less than this estimate.
- The window is one machine, one user and one repository mix. It is not a
  benchmark, a controlled before/after experiment or a comparable-task sample.

## Verify

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/pi_usage_report.py
```

The suite checks the arithmetic against a hand-computed fixture, the replay
estimate against a hand computation, missing-usage honesty, malformed-line
tolerance, timestamp filtering and every privacy property above.
