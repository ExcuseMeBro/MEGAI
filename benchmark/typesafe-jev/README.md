# TypeSafe Jev decision benchmark

Measures whether a TypeSafe System One call replaces a model prompt for a triage
step: 24 labelled repository requests, answered by `jev` (typed `choice` + `score` +
`noul` questions), by `pi:deepseek/deepseek-flash`, and by `pi:minimax/MiniMax-M3`
on the same strict-JSON prompt.

Published run: [results/jev-decisions.md](results/jev-decisions.md) with the
sanitized per-call records in
[results/jev-decisions.trials.json](results/jev-decisions.trials.json). Jev alone is
measured in [results/micro-bench.md](results/micro-bench.md): latency, cost, state
and question scaling, and repeat consistency.

## Files

| File | Purpose |
| --- | --- |
| `items.json` | The 24 requests with their author labels, plus the label policy text every arm receives verbatim |
| `run_jev_bench.py` | Runner and report; raw responses stay in the private `--root` directory |
| `micro_bench.py` | Jev-only runner and report for the micro-benchmark; same private `--root` rule |
| `results/` | Published summaries and sanitized records |

## Run

```bash
export TYPESAFE_API_KEY=...      # read from the environment; never written to a record
python3 benchmark/typesafe-jev/run_jev_bench.py run --root DIR --results DIR/trials.jsonl
python3 benchmark/typesafe-jev/run_jev_bench.py report --results DIR/trials.jsonl
```

- `run` is resumable: recorded `(arm, item)` pairs are skipped, so an interrupted
  run continues instead of repeating paid calls.
- The two Pi arms run in the neutral `--root/cwd` directory, so no project rules or
  skills enter their prompt, with thinking `medium` for both.
- The Jev call uses the system CA bundle (`/etc/ssl/cert.pem`) because a python.org
  interpreter ships none; stdlib only, no dependency.

## Read the results carefully

- Labels are author-assigned against this repository's own classification table,
  not an external gold set; at least one label is demonstrably contestable.
- 24 items and one run per item is a smoke test: differences of one or two items are
  inside noise, and effort placement is the weakest field.
- Jev's `score` is probability-weighted and can land between levels; the level
  reported here is its rounded position and the raw value is kept in the records.
- Token columns are not comparable across providers; `cost_usd` is.
