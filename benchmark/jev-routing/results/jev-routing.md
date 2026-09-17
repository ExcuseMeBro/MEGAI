# Jev model routing: deepseek-flash vs MiniMax-M3

Can one TypeSafe decision call route a repository request to the cheaper or the stronger
model as well as always using one of them? 24 labelled requests from
[`../typesafe-jev/items.json`](../typesafe-jev/items.json), one run each, three arms.

| Arm | Interface |
| --- | --- |
| `pi:deepseek/deepseek-flash` | fixed baseline: the cheap model answers every item |
| `pi:minimax/MiniMax-M3` | fixed baseline: the expensive model answers every item |
| `jev-route` | one Jev `choice` call (`deepseek-flash` / `MiniMax-M3` / `either`) plus a `hard` probability per item, then the chosen model answers the identical strict-JSON prompt |

Every arm sees the same policy text and the same request; the routed arm differs only in
which model was asked, and the router's own tokens and wall time are charged to it.
Records: [`results/jev-routing.trials.json`](jev-routing.trials.json). Total experiment
cost: **$0.1372** for 72 calls, of which the 24 routing calls were $0.000752 (p50 0.78 s).

**No significance claim.** 24 items and one run per item is a smoke test, and the same
model answered 7 of 24 items differently on a second identical run (below), so a one- or
two-item gap carries no information.

## Headline

Routing matched always-deepseek and bought nothing: same cost (1.01x), same correctness
(12/24), and it picked the strong model twice — both times wrongly. Always-MiniMax scored
one item better at 3.79x the cost, which is inside noise. On this set, the useful signal
was not *which* model answers but Jev's difficulty estimate: it was higher on the items
the models got wrong.

## Arms

| Arm | type | effort | ±1 | approval | whole answer correct | p50 s | p95 s | cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pi:deepseek/deepseek-flash` | 23/24 | 13/24 | 24/24 | 24/24 | **12/24** | 6.0 | 7.9 | $0.023621 |
| `pi:minimax/MiniMax-M3` | 22/24 | 13/24 | 24/24 | 24/24 | **13/24** | 3.6 | 5.8 | $0.089634 |
| `jev-route` | 22/24 | 13/24 | 23/24 | 24/24 | **12/24** | 6.7 | 8.9 | $0.023955 |

Whole answer correct means type, effort level and approval flag all exactly right;
approval was the one field every arm got right on every item.

## Routing

| Measure | Value |
| --- | --- |
| Routed to `deepseek-flash` | 22/24 (mean `P(deepseek-flash)` on those items 0.82) |
| Routed to `MiniMax-M3` | 2/24 — `t11` and `t24`, both answered wrongly by the chosen model |
| Routing call failed (fallback to the cheap model) | 0 |
| Oracle: cheapest fully-correct fixed arm | deepseek 12, minimax 5, neither correct 7 |
| Router chose a model that was fully correct that item | 11/24 |
| Losses: routed answer failed where a fixed arm passed | 5 — `t05`, `t10`, `t15`, `t17`, `t24` |
| Same-model replay: routed answer identical to that model's fixed run | 17/24 (differing: `t02`, `t07`, `t15`, `t17`, `t18`, `t23`, `t24`) |

Of the 5 losses, 3 (`t15`, `t17`, `t24`) are also replay differences — the same model
answered differently twice on the same prompt — so they are answer variance, not routing
mistakes. Only `t05` and `t10` are genuine routing misses: MiniMax was fully correct there
and the router still sent the work to the cheap model.

Signal quality over the 24 items (small n, directional only):

| Signal | Correct items | Incorrect items |
| --- | --- | --- |
| mean Jev `hard` (needs more reasoning) | 0.38 (n=12) | 0.52 (n=12) |
| mean Jev model-choice confidence | 0.75 (n=12) | 0.64 (n=12) |

The difficulty estimate separated the outcomes in the right direction and the confidence
did too, but the *model choice* it produced was strongly biased to the cheap model and
made no difference to the result.

## Limits

- The **oracle is an upper bound built from this same run** — the cheapest arm that
  happened to be fully correct per item. It is not an achievable baseline, and its cost
  ($0.036660) is above the routed arm's precisely because the items where only MiniMax was
  correct are expensive.
- One run per item. Replay disagreement of 7/24 bounds how much any arm-level difference
  here can mean.
- The work is triage answering: classify a request text. The models are far more likely to
  differ on implementation, debugging or review work, which this set does not contain.
- Labels are author-assigned against this repository's classification table, not an
  external gold set; effort placement is the softest field (13/24 for every arm, ±1 for
  nearly all).

## Reproduce

```bash
export TYPESAFE_API_KEY=...      # read from the environment; never written to a record
python3 benchmark/jev-routing/run_routing_bench.py run --root DIR --results DIR/trials.jsonl
python3 benchmark/jev-routing/run_routing_bench.py report --results DIR/trials.jsonl
```

Raw per-call responses stay in the private `--root`; the published records above are
sanitized copies (no key material, requests kept as sha256).

## What this does not authorize

No auto-switching of models in real tasks, no change to approval, review or delivery
rules. The next cheap experiment, if wanted, is either k-repeat runs to get above the
replay noise, or rerouting the same Jev signal into a *verification* decision ("does this
answer need a second model or a check?") instead of a model choice, since the difficulty
estimate is the part that carried information.
