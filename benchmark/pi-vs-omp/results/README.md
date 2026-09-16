# Pi vs OMP pilot results

48/48 trials are valid model runs: four models, two thinking levels, three tasks,
both harnesses, one run per cell. Full tables are in [summary.md](summary.md);
sanitized per-trial records (tokens, cost, wall time, acceptance, scope) are in
[trials.json](trials.json).

**No winner is claimed.** Both arms passed every frozen acceptance suite, so
acceptance cannot separate them on these three small exercises; that is the main
result and the main limitation.

## Headline

| Arm | Harness | Trials | Acceptance | Wall s (sum) | Wall s (median) | Total tokens | Uncached input | Output | Reported cost | Cache share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pi | `pi` 0.85.1 | 24 | 24/24 | 1927 | 87.7 | 5,743,727 | 770,975 | 74,832 | $5.86 | 85.3% |
| omp | `omp/18.2.0` | 24 | 24/24 | 1886 | 86.8 | 6,168,200 | 699,727 | 82,873 | $5.42 | 87.3% |

- Wall time is a wash: OMP is 2.1% faster in total, Pi 0.9s faster at the median.
- Pi used 6.9% fewer total tokens; OMP cached more of its input (87.3% vs 85.3%)
  and therefore reported 7.4% lower cost despite the larger token total.
- Both harnesses were scope-clean in all 48 trials: only the two allowed paths
  changed, no acceptance failures, no deadline overruns, no model substitutions.

## Baseline context

Same checkout, trivial prompt, thinking off: Pi carries **17,340** context tokens,
OMP **21,844** (+26%) — system prompt plus loaded skills/rules. This is the
per-request overhead difference that the aggregate input column reflects.

## Per model (Pi / OMP)

| Model | Wall s (sum) | Total tokens | Reported cost |
| --- | --- | --- | --- |
| deepseek-flash | 127 / 173 | 1,120,476 / 1,363,661 | $0.05 / $0.03 |
| gpt-5.6-luna | 599 / 539 | 1,703,153 / 1,828,534 | $0.12 / $0.11 |
| gpt-5.6-sol | 667 / 673 | 1,672,523 / 1,551,035 | $2.28 / $1.76 |
| gpt-6-astra | 533 / 500 | 1,247,575 / 1,424,970 | $3.40 / $3.53 |

The only consistent per-model gap is DeepSeek Flash: Pi finished 27% faster on
that model with 18% fewer tokens. The GPT-6 results move by only a few percent in
either direction, which is inside single-run noise.

## Environment failures excluded from the tables

An earlier attempt recorded 19 trials that produced no provider usage at all —
both harnesses reported `stopReason: error` (`Was there a typo in the url or
port?`), and some runs outlasted their 300-second budget while the machine slept.
Those attempts were diagnosed as environment failures, not model results, and
re-run. They are preserved in the private evidence directory; they are not in
`trials.json`. Only the successful re-runs are published.

## Evidence

- Raw harness JSON streams, candidate diffs, evaluation output and per-trial
  checkouts: private directory passed to `run_bench.py --root` (outside the repo).
- Published: this file, `summary.md`, `trials.json`.
- Reproduce: see [../README.md](../README.md).
