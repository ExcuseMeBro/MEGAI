# Role thinking levels — deepseek-flash low vs high

Six fresh trials on the same frozen fixtures as the harness pilot, one run per cell:
the `pi` arm, `deepseek/deepseek-flash`, thinking `high` (the previous role level for
planner, scout and worker) against `low`, on all three tasks. Raw records:
`~/.megai/benchmarks/pi-thinking-levels/results.jsonl` (private evidence directory);
the sanitized per-trial numbers are reproduced below.

Baseline: `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1` | harness `pi` 0.85.1 | budget 300s
Method, tasks, acceptance suites and scope check: [../README.md](../README.md).

## Per-trial results

| Thinking | Task | Acceptance | Wall s | Requests | Input | Output | Reasoning | Cache read | Total | Reported cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high | bugfix | 10 PASS | 14.3 | 5 | 13,118 | 1,996 | 458 | 88,192 | 103,306 | $0.0069 |
| low | bugfix | 10 PASS | 14.1 | 7 | 20,371 | 1,595 | 280 | 121,600 | 143,566 | $0.0088 |
| high | feature | 12 PASS | 24.5 | 8 | 15,687 | 3,833 | 1,657 | 166,784 | 186,304 | $0.0103 |
| low | feature | 12 PASS | 16.6 | 8 | 13,803 | 2,001 | 473 | 151,168 | 166,972 | $0.0074 |
| high | refactor | 10 PASS | 28.0 | 8 | 14,656 | 4,711 | 2,467 | 159,104 | 178,471 | $0.0110 |
| low | refactor | 10 PASS | 18.6 | 8 | 14,059 | 2,540 | 606 | 153,216 | 169,815 | $0.0082 |

## Aggregate

| Thinking | Tasks passed | Tests | Wall s (sum) | Wall s (median) | Requests | Output | Reasoning | Total tokens | Reported cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| high | 3/3 | 32 | 66.8 | 24.5 | 21 | 10,540 | 4,582 | 468,081 | $0.0282 |
| low | 3/3 | 32 | 49.3 | 16.6 | 23 | 6,136 | 1,359 | 480,353 | $0.0244 |

- **Acceptance is unchanged**: 3/3 tasks, 32/32 frozen tests at both levels, and every
  trial stayed inside the two allowed paths with no model substitution and no deadline.
- **Low is 26% faster** in total wall time (49.3s vs 66.8s) and 32% faster at the median.
- **Low reports 13% lower cost** with 42% fewer output tokens and 70% fewer reasoning
  tokens, but 2.6% more total tokens: it made two extra requests and re-used less cached
  input. Cost follows cache behaviour more than token count here.

## What this changes

`pi-skill/presets/economy.json` now runs scout and worker at `low` and keeps the planner
at `high`, so one cheap model plans with judgment and executes cheaply. Roles that share a
model keep their own level in `megai-roles.json`; `settings.json` keeps the planner's level
as the unambiguous native startup default.

## Limits

- One run per cell. This is an exploratory pilot, not a distribution, and no significance
  is claimed for the 13% cost gap, which is inside single-run noise on these fixtures.
- Scout work (search, read, call-graph discovery) is not covered by these three tasks. Its
  `low` level follows the executor evidence and the role's read-only nature, and is
  unmeasured.
- Reported cost is the harness's own estimate from host-reported counters, not billing.
- Readability, review quality, large-repository work, UI work and security work are out of
  scope, as in the harness pilot.
