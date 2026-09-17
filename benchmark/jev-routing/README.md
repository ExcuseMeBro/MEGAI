# Jev model routing benchmark

Measures whether one TypeSafe System One call can route a request to the cheaper or the
stronger Pi model as well as always using one of them: 24 labelled repository requests,
answered by `pi:deepseek/deepseek-flash`, by `pi:minimax/MiniMax-M3`, and by a
`jev-route` arm that makes one Jev model-choice call per request and then lets the chosen
model answer the identical prompt.

Published run: [results/jev-routing.md](results/jev-routing.md) with the sanitized
per-call records in [results/jev-routing.trials.json](results/jev-routing.trials.json).

## Arms

| Arm | What it does |
| --- | --- |
| `pi:deepseek/deepseek-flash` | Fixed baseline; the cheap model answers every item |
| `pi:minimax/MiniMax-M3` | Fixed baseline; the expensive model answers every item |
| `jev-route` | One Jev `choice` question (`deepseek-flash` / `MiniMax-M3` / `either`) plus a `hard` probability, then the chosen model answers. Router tokens and wall time are added to the arm's own cost |

A failed or choice-less routing call falls back to the cheaper model and is recorded as
`route_failed`, never retried.

## Files

| File | Purpose |
| --- | --- |
| `run_routing_bench.py` | Runner and report; imports the fixture, the answer prompt and the Pi/Jev plumbing from `benchmark/typesafe-jev` so both benchmarks stay comparable |
| `../typesafe-jev/items.json` | The shared 24 requests, author labels and policy text (single source; not duplicated here) |
| `results/` | Published summary and sanitized records |

## Run

```bash
export TYPESAFE_API_KEY=...      # read from the environment; never written to a record
python3 benchmark/jev-routing/run_routing_bench.py run --root DIR --results DIR/trials.jsonl
python3 benchmark/jev-routing/run_routing_bench.py report --results DIR/trials.jsonl
```

- `run` is resumable by `(arm, item)`, so an interrupted run continues instead of
  repeating paid calls; `--arms` runs a subset.
- Both Pi arms run in the neutral `--root/cwd` directory with thinking `medium`, so no
  project rules enter their prompt and the only difference between a routed and a fixed
  run is which model was asked.
- `TYPESAFE_API_KEY` is only read from the environment. Never commit it, and keep the raw
  `--root` responses private.

## Read the results carefully

- The **oracle** is the cheapest fixed arm that answered an item fully correctly *in this
  same run*. It is an upper bound assembled from both models' answers, not a model's real
  capability, so "regret" measures distance from that bound, not from truth.
- 24 items, one run per item: one- or two-item differences are noise. The router's value
  only shows up if it loses no correctness at a materially lower cost.
- The work here is triage answering — classifying a request text. A routing win on this
  set is evidence about that step only, not about implementation, debugging or review
  work, which is where the models are more likely to differ.
- `router_pick_hit` asks whether the router chose a model that turned out to be fully
  correct; `lost` asks whether the routed *answer* failed where a fixed arm passed. The
  second is the number that matters, and it counts both routing mistakes and answer
  noise.
- Token columns are not comparable across providers; `cost_usd` is, and it already
  includes the router's own tokens.

## What a positive result justifies, and what it does not

It justifies a documented routing policy (and, optionally, a runtime router behind a flag
that reuses `pi.setModel`). It does not by itself justify automatic model switching in
real tasks, and it changes no approval, review or delivery rule.
