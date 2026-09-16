# Pi vs OMP pilot results

48/48 trials are valid model runs: four models, two thinking levels, three tasks,
both harnesses, one run per cell. Full tables are in [summary.md](summary.md);
sanitized per-trial records (tokens, cost, wall time, acceptance, scope) are in
[trials.json](trials.json).

A later six-trial rerun on the `pi` arm compares the DeepSeek `high` and `low` role
thinking levels that the economy preset selects:
[thinking-levels.md](thinking-levels.md).

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

## Runtime footprint (RAM and CPU)

Measured with `/usr/bin/time -l` around the harness process; RSS is that process's
peak resident set, not the whole desktop session. Runs are the same frozen fixture
as the trials.

| Arm | Scenario | Peak RSS MB | Peak footprint MB | CPU s | CPU % of wall | Wall s |
| --- | --- | --- | --- | --- | --- | --- |
| pi | idle request | 211.6 | 133.1 | 3.07 | 39.4 | 7.8 |
| omp | idle request | 553.8 | 414.9 | 5.52 | 55.0 | 10.1 |
| pi | bugfix + deepseek-flash medium | 220.2 | 133.0 | 3.95 | 10.0 | 40.2 |
| omp | bugfix + deepseek-flash medium | 649.9 | 417.3 | 10.75 | 22.7 | 47.4 |

Note: the `deepseek-flash medium` rows above are mislabeled — `medium` maps to `null` in that
model's Pi entry, so those runs sent no thinking parameter. The trial numbers stand; the label
does not describe two thinking levels. See [thinking-levels.md](thinking-levels.md).
| pi | bugfix + gpt-6-astra high | 211.6 | 132.7 | 4.30 | 2.4 | 182.0 |
| omp | bugfix + gpt-6-astra high | 583.2 | 413.9 | 11.33 | 7.9 | 143.4 |

- **RAM: OMP needs 2.6–3.0× more.** ~554–650 MB peak versus ~211–220 MB for Pi;
the gap is ~340–430 MB per session and is already present on an idle one-token
request, so it comes from the runtime itself, not from task size.
- **CPU: OMP burns 2.5–2.7× more.** 5.5–11.3 CPU-seconds per run versus
  3.1–4.3 for Pi. Idle CPU share is 55% (OMP) versus 39% (Pi); on the GPT-6 run,
  where wall time is provider-bound, Pi stays at 2.4% against 7.9%.
- Memory is flat across scenarios for both arms, so the footprint is a property of
  the harness, not of the model or task.

## Disk footprint

| Item | Pi | OMP |
| --- | --- | --- |
| Harness runtime package | 23 MB (`@earendil-works/pi-coding-agent`) | 259 MB (`@oh-my-pi/*`, of which 162 MB `pi-natives-darwin-arm64`) |
| Profile directory | 743 MB `~/.pi/agent` (372 MB `tools`, 294 MB `npm`, 75 MB `sessions`) | 11 MB `~/.omp/agent` (6.8 MB `models.db`, 4.0 MB `agent.db-wal`) |
| Shared MEGAI tools | 7.8 GB `~/.megai` | same directory |

This is not a like-for-like delta: Pi fetches extensions and tool runtimes into its
profile (`pi-superpowers`, `pi-mcp-adapter`, `pi-web-access`, Ponytail, pinned
Headroom/tgrep/codedb), while OMP ships its native binaries inside the package.
Only the runtime package line compares equivalently, and there Pi is 11× smaller.

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
