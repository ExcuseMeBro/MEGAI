# MiniMax-M3 mixed with deepseek-flash — results

Measures what the paid MiniMax-M3 adds to the paid deepseek-flash worker. The
request was *"benchmark the minimax + deepseek combination in Pi, with the Jev
decision tool active by default"*, so both mixing directions are measured next to
each model working alone, and the review control from the local-Qwen run is
repeated in the same session for a same-window comparison.

Arms, all on the frozen `capy` exercises, Pi harness, one run per cell:

| Arm | `--arm` | Worker | Reviewer |
| --- | --- | --- | --- |
| deepseek alone | `pi` | `deepseek/deepseek-flash` | none |
| MiniMax alone | `pi` | `minimax/MiniMax-M3` | none |
| **mixed (MiniMax worker)** | `hybrid` | `minimax/MiniMax-M3` | `deepseek/deepseek-flash` |
| **mixed (MiniMax reviewer)** | `hybrid` | `deepseek/deepseek-flash` | `minimax/MiniMax-M3` |
| review control | `hybrid` | `deepseek/deepseek-flash` | `deepseek/deepseek-flash` |

Baseline `095a664e` | 15/15 valid | all arms asked for `high` thinking | task budget 1200 s.

## Headline

**MiniMax-M3 costs 3× more per task than deepseek-flash here and is 2.4× slower,
at identical acceptance — and mixing it in makes both worse, not better.** All 15
trials passed the frozen acceptance suites, every worker passed its own acceptance
*before* its reviewer ran (9/9 mixed trials), and one of 15 reviewers touched a
line of code at all — a defensive one-liner (`status not in counts` →
`_STATUSES`) in a trial whose worker had already passed acceptance.

| Arm | Trials | Acceptance | Wall s (sum) | Wall s (median) | Requests | Uncached input | Output | Cache read | Reported cost | Cost per task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pi` + deepseek-flash (worker only) | 3 | 3/3 | 76.7 | 29.3 | 27 | 43546 | 12517 | 585984 | $0.03160 | $0.01053 |
| `pi` + MiniMax-M3 (worker only) | 3 | 3/3 | 183.8 | 52.7 | 38 | 106353 | 12342 | 771857 | $0.09303 | $0.03101 |
| `hybrid` + MiniMax-M3 (MiniMax worker -> deepseek reviewer) | 3 | 3/3 | 280.6 | 85.6 | 75 | 120875 | 25971 | 1649250 | $0.13912 | $0.04637 |
| `hybrid` + deepseek-flash (deepseek worker -> MiniMax reviewer) | 3 | 3/3 | 200.2 | 60.0 | 63 | 113597 | 18511 | 1291616 | $0.10502 | $0.03501 |
| `hybrid` + deepseek-flash (deepseek worker -> deepseek reviewer) | 3 | 3/3 | 134.0 | 48.6 | 51 | 65670 | 20801 | 1143168 | $0.05152 | $0.01717 |

- **No MiniMax configuration wins anything measurable.** The cheapest arm is
  deepseek alone at $0.01053/task; the cheapest arm containing MiniMax-M3 is
  deepseek worker with a MiniMax reviewer at $0.03501/task (3.3×), and MiniMax as
  the worker is the worst of all (3.0× alone, 2.7× in the mix over the deepseek
  control). Wall time moves the same way: 76.7 s vs 183.8–280.6 s.
- **Acceptance is tied at 3/3 in all five arms**, and `participant`/acceptance
  `scope_ok` is `true` for all 15 trials. Three one-file exercises cannot separate
  two frontier-class models; this run does not claim MiniMax is *worse*, only that
  it is more expensive and slower on this workload.
- **The review stage is the tax, and it buys nothing here.** Review-only cost is
  22% of the MiniMax-worker mix, 37% of the deepseek control, and **71%** of the
  MiniMax-reviewer mix — where the reviewer alone costs $0.02190–$0.02812 per task,
  more than twice what deepseek charges for the entire job.
- **MiniMax-M3 is not cheaper per token.** Both models list at $0.30/M input and
  $1.20/M output; the difference is prompt-cache reads at $0.06/M versus
  deepseek-flash's $0.006/M. With Pi's ~18.5k-token system prompt re-sent on every
  turn, cache reads are 50% of the MiniMax arm's bill ($0.04631 of $0.09303) but
  only 11% of deepseek's ($0.00352 of $0.03160).

## Per task

| Task | deepseek alone $ | s | MiniMax alone $ | s | MiniMax worker + deepseek reviewer $ | s | deepseek worker + MiniMax reviewer $ | s | deepseek worker + deepseek reviewer $ | s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bugfix | $0.00740 | 15.1 | $0.02747 | 46.8 | $0.03527 | 54.1 | $0.03607 | 53.4 | $0.01419 | 33.2 |
| feature | $0.01138 | 29.3 | $0.02239 | 84.3 | $0.05825 | 85.6 | $0.03267 | 86.7 | $0.01929 | 52.1 |
| refactor | $0.01282 | 32.3 | $0.04316 | 52.7 | $0.04560 | 140.9 | $0.03628 | 60.0 | $0.01804 | 48.6 |

## Per-trial results

| Arm | Task | Worker s | Reviewer s | Total s | Worker $ | Reviewer $ | Total $ | Worker acceptance | Reviewer code change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pi` + deepseek-flash | bugfix | 15.1 | n/a | 15.1 | $0.00740 | n/a | $0.00740 | pass | n/a (no review stage) |
| `pi` + deepseek-flash | feature | 29.3 | n/a | 29.3 | $0.01138 | n/a | $0.01138 | pass | n/a (no review stage) |
| `pi` + deepseek-flash | refactor | 32.3 | n/a | 32.3 | $0.01282 | n/a | $0.01282 | pass | n/a (no review stage) |
| `pi` + minimax-m3 | bugfix | 46.8 | n/a | 46.8 | $0.02747 | n/a | $0.02747 | pass | n/a (no review stage) |
| `pi` + minimax-m3 | feature | 84.3 | n/a | 84.3 | $0.02239 | n/a | $0.02239 | pass | n/a (no review stage) |
| `pi` + minimax-m3 | refactor | 52.7 | n/a | 52.7 | $0.04316 | n/a | $0.04316 | pass | n/a (no review stage) |
| `hybrid` + minimax-m3 (reviewer deepseek-flash) | bugfix | 35.3 | 18.6 | 54.1 | $0.02670 | $0.00856 | $0.03527 | pass | none |
| `hybrid` + minimax-m3 (reviewer deepseek-flash) | feature | 62.5 | 22.8 | 85.6 | $0.04766 | $0.01059 | $0.05825 | pass | none |
| `hybrid` + minimax-m3 (reviewer deepseek-flash) | refactor | 110.8 | 30.0 | 140.9 | $0.03362 | $0.01199 | $0.04560 | pass | yes (one line) |
| `hybrid` + deepseek-flash (reviewer minimax-m3) | bugfix | 16.4 | 36.9 | 53.4 | $0.00795 | $0.02812 | $0.03607 | pass | none |
| `hybrid` + deepseek-flash (reviewer minimax-m3) | feature | 27.2 | 59.4 | 86.7 | $0.01077 | $0.02190 | $0.03267 | pass | none |
| `hybrid` + deepseek-flash (reviewer minimax-m3) | refactor | 28.6 | 31.2 | 60.0 | $0.01200 | $0.02428 | $0.03628 | pass | none |
| `hybrid` + deepseek-flash (reviewer deepseek-flash) | bugfix | 18.5 | 14.5 | 33.2 | $0.00911 | $0.00508 | $0.01419 | pass | none |
| `hybrid` + deepseek-flash (reviewer deepseek-flash) | feature | 29.9 | 22.0 | 52.1 | $0.01149 | $0.00780 | $0.01929 | pass | none |
| `hybrid` + deepseek-flash (reviewer deepseek-flash) | refactor | 29.5 | 18.9 | 48.6 | $0.01168 | $0.00636 | $0.01804 | pass | none |

`Worker acceptance` is the acceptance suite run against the worker's diff *before*
the reviewer touched it. `Reviewer code change` compares the two diffs ignoring
`__pycache__`; the single "yes" is
`if status not in counts:` → `if status not in _STATUSES:` where both the pre- and
post-review suites passed 10/10.

## Why MiniMax is the more expensive side

| Effect | Measured |
| --- | --- |
| List price per token | $0.30/M in, $1.20/M out for **both** models |
| Prompt-cache read price | MiniMax $0.06/M vs deepseek $0.006/M (10×) |
| Cache reads per task | 195k (deepseek alone), 257k (MiniMax alone), 381k (deepseek control), 430k–550k (the two MiniMax mixes) |
| Requests per task | 9 (deepseek) vs 13 (MiniMax) vs 25 (MiniMax worker + reviewer) |
| Output tokens per task | ~4.1k in both single-model arms |
| Review-stage cost share | 22% / 37% / **71%** (MiniMax worker / deepseek control / MiniMax reviewer) |

MiniMax's extra turns, not its token prices, produce the difference: the same
output volume at the same unit price, re-reading a 10×-priced prompt cache each time.

## Jev status in these trials

The Pi profile used for every trial is the live MEGAI profile, which loads the
`megai-jev` extension by default. `jev` was available to all 15 agents and **was
called zero times**: 584 tool calls were `bash` (400), `read` (120), `write` (50)
and `edit` (14). These prompts hand the agent its arm, model and thinking level, so
there is no triage decision left for Jev to answer — the measurement says nothing
about Jev's value on an unclassified request, only that it adds no cost when idle.

The tool was also **broken** at the start of this task: the live endpoint answers a
`choice`/`noul` `criteria` *list* with HTTP 422 and requires `criteria` on `choice`
and `score`, which made every triage call fail open with no answer. The fix
(normalize by question type before the request) is part of this change and was live
before the matrix ran — see the delivery commit and `pi-skill/jev/index.ts`.

## Limits

- Three small frozen exercises (one file each, public seam) and one run per cell.
  n=3 per arm: a one-task or one-cent difference is noise, and no repeatability was
  measured.
- Acceptance is the only quality signal. These exercises cannot show where
  MiniMax-M3 would pull ahead on a large, ambiguous change; the results claim cost
  and wall time, not a general quality order.
- Cost is the provider's reported number, not a bill. Token-basis comparison across
  providers is not meaningful here; `cost_usd` is.
- The reviewer re-establishes full repository context (re-reads files, reruns the
  suite), so these review costs are the cost of a context-heavy review, not of a
  diff-scoped one.
- The first cell (`pi` + deepseek-flash, bugfix) was run as a smoke test with the
  harness's 300 s default budget and recorded as such; it finished in 15.1 s, far
  below both budgets.

## Environment

| Item | Value |
| --- | --- |
| Harness | Pi 0.85.1, `pi -p --mode json --no-session -a --model … --thinking high` |
| MiniMax-M3 | `minimax/MiniMax-M3`, anthropic-messages endpoint, reasoning on, 512k max output |
| deepseek-flash | `deepseek/deepseek-flash`, 200k context, prompt cache enabled |
| Profile | live `~/.pi/agent` MEGAI profile (headroom, jev, provider guard, role routing, workspace guard) |

## Evidence

- Private (`~/.megai/evidence/minimax-hybrid/`): `trials.jsonl`, raw `harness*.jsonl`
  streams, per-trial prompts, `worker.diff` / `candidate.diff`, evaluation output and
  per-trial checkouts for all 15 trials, `run_matrix.sh`, `make_report.py`, `tables.md`.
- Published: this file and `minimax-hybrid.trials.json` (15 records, one per trial id,
  no raw provider payloads, no credentials).
- Reproduce one mixed cell:

```sh
python3 benchmark/pi-vs-omp/run_bench.py trial \
  --arm hybrid --model deepseek/deepseek-flash --reviewer minimax/MiniMax-M3 \
  --thinking high --task bugfix --baseline BASELINE --root DIR --results DIR/trials.jsonl
```
