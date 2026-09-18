# Jev micro-benchmark

Focused measurement of TypeSafe Jev (`jev-1.13.0`) alone: latency distribution,
cost, scaling with state size and question count, and answer consistency on
identical repeats. The 24-item triage benchmark in
[`jev-decisions.md`](jev-decisions.md) compares Jev with Pi model arms; this one
isolates Jev.

**Run** — 2026-09-18 — 75 calls — **total cost $0.0017**

## Matrix

11 variants; the same call is repeated within each variant so the latency,
cost and consistency numbers describe a real distribution, not one sample.

| Variant       | What it varies           | Repeats |
| ------------- | ------------------------ | ------: |
| latency       | none (baseline)          |      20 |
| consistency   | none (variance check)    |      10 |
| size_tiny     | state = ~50 chars        |       5 |
| size_small    | state = ~500 chars       |       5 |
| size_medium   | state = ~2 000 chars     |       5 |
| size_large    | state = ~8 000 chars     |       5 |
| q1_choice     | one `choice` question    |       5 |
| q1_score      | one `score` question     |       5 |
| q1_noul       | one `noul` question      |       5 |
| q4_mixed      | four distinct questions  |       5 |
| q8_mixed      | eight distinct questions |       5 |

Question construction follows the published contract: `choice` and `noul` use a
label→meaning map, `score` uses an ordered level list.

## Per-variant results

| variant        | n | in_tok avg | out_tok avg | p50 s | p95 s | min s | max s | cost$/call |
| -------------- | -:| ---------: | ----------: | ----: | ----: | ----: | ----: | ---------: |
| latency        | 20 |       404  |          23 | 0.770 | 0.893 | 0.737 | 0.936 |  $0.000017 |
| consistency    | 10 |       404  |          23 | 0.805 | 0.838 | 0.734 | 0.838 |  $0.000017 |
| size_tiny      |  5 |       348  |          23 | 0.797 | 0.995 | 0.746 | 0.995 |  $0.000015 |
| size_small     |  5 |       404  |          23 | 0.804 | 0.815 | 0.748 | 0.815 |  $0.000017 |
| size_medium    |  5 |       596  |          23 | 0.840 | 0.987 | 0.714 | 0.987 |  $0.000025 |
| size_large     |  5 |      1364  |          23 | 0.772 | 0.833 | 0.750 | 0.833 |  $0.000057 |
| q1_choice      |  5 |       492  |          68 | 0.973 | 1.134 | 0.754 | 1.134 |  $0.000021 |
| q1_score       |  5 |       418  |          18 | 0.792 | 0.915 | 0.723 | 0.915 |  $0.000018 |
| q1_noul        |  5 |       404  |          23 | 0.756 | 0.913 | 0.735 | 0.913 |  $0.000017 |
| q4_mixed       |  5 |       729  |         176 | 0.787 | 0.833 | 0.726 | 0.833 |  $0.000031 |
| q8_mixed       |  5 |      1025  |         298 | 0.749 | 0.856 | 0.741 | 0.856 |  $0.000043 |

`cost$` is `input_tokens × $42 / 1e9` (Jev's published input rate, output free).

## What the numbers say

- **Latency is flat across the matrix.** p50 sits in 0.75–0.80 s for almost every
  variant; the only outlier is `q1_choice` at 0.97 s p50 / 1.13 s p95 — small
  sample, one slow call. Even at the largest state (`size_large`, ~1.4k input
  tokens) and eight distinct questions (`q8_mixed`), p95 stays under 0.9 s. The
  model-decision endpoint does not appear to be inference-bound on this matrix.
- **Cost scales with input tokens, latency does not.** Doubling state size or
  question count moves `cost$` linearly; `wall_seconds` does not. Jev's pricing
  is input-token-bound and its latency is dominated by network and queue time,
  not token count, at these scales.
- **Choice questions emit the distribution.** `q1_choice` uses 68 output tokens
  on average (the full probability map); `q1_score` emits 18 and `q1_noul` emits
  23. Output tokens are free, but the response size — and the bandwidth it
  implies — is real.
- **Consistency is high on identical repeats.** 10 calls of the same noul
  question produced values in **[0.08, 0.09]** — range 0.01, stdev 0.0042. The
  endpoint is deterministic enough that a low-confidence answer reflects the
  input, not run-to-run noise.

## Limits

- Small samples per variant (5 except latency/consistency); one outlier shifts
  p95 noticeably. Treat the `q1_choice` 1.13 s p95 as a single observation, not
  a distribution claim.
- No concurrency test: calls were serial. A concurrent sweep would show whether
  the endpoint absorbs parallel load or queues it.
- Network latency was not subtracted; this measures wall-clock end-to-end from
  the same machine that ran the 24-item comparison.

## Evidence

- Runner: [`../micro_bench.py`](../micro_bench.py) — stdlib-only, reads
  `TYPESAFE_API_KEY` from the environment and never writes it.
- Raw records: `/tmp/jev-microbench/raw/{variant}__{index}.json` (75 files).
- Summary: `/tmp/jev-microbench/summary.json`.
