# Pi vs OMP harness benchmark — results

> **Scope.** Pi arm only (`--arms pi`; OMP is not installed on this host, so the Pi/OMP pairing
> table below is empty). Compared model: `openrouter/stealth/union-alpha` (OpenRouter free
> stealth preview, 262K context, no reasoning control) against `deepseek/deepseek-flash`.
> Cells: three frozen tasks x {union-alpha at the requested `high` level, union-alpha at `off`,
> deepseek-flash at `high` and `low`}, one run per cell except provider-failed cells, which are
> listed under *Excluded*. Baseline `095a664e`. Records: `union-alpha.trials.json` — one record
> per trial id: the valid attempt when one exists, otherwise one failed attempt.


Baseline: `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1` | valid trials: 9 | task budget: 300s

Excluded as environment failures, not model results: 3 trial(s) with no provider usage, a provider error, or a run that outlasted its budget.

| Excluded trial | Wall s | Requests | Total tokens | Stop reasons |
| --- | --- | --- | --- | --- |
| pi__union-alpha__high__bugfix | 75.9 | 3 | 37325 | toolUse, toolUse, error |
| pi__union-alpha__high__refactor | 126.7 | 4 | 59205 | toolUse, toolUse, error |
| pi__union-alpha__off__bugfix | 62.8 | 2 | 18229 | toolUse, error |

## Per-trial results

| Arm | Model | Thinking | Task | Wall s | Reqs | Input | Output | Cache read | Total | Cost | Acceptance | Participant | Scope | Stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pi | deepseek-flash | high | bugfix | 23.2 | 9 | 14261 | 3488 | 182272 | 200021 | $0.0096 | 10 PASS | 3 PASS | ok | exit 0 |
| pi | deepseek-flash | high | feature | 22.5 | 9 | 14399 | 3352 | 187392 | 205143 | $0.0095 | 12 PASS | 5 PASS | ok | exit 0 |
| pi | deepseek-flash | high | refactor | 29.5 | 8 | 14508 | 5098 | 169728 | 189334 | $0.0115 | 10 PASS | none | ok | exit 0 |
| pi | deepseek-flash | low | bugfix | 13.4 | 6 | 13160 | 1542 | 111488 | 126190 | $0.0065 | 10 PASS | 3 PASS | ok | exit 0 |
| pi | deepseek-flash | low | feature | 14.3 | 6 | 14055 | 2214 | 116224 | 132493 | $0.0076 | 12 PASS | 4 PASS | ok | exit 0 |
| pi | deepseek-flash | low | refactor | 24.6 | 8 | 14166 | 4002 | 166912 | 185080 | $0.0101 | 10 PASS | 4 PASS | ok | exit 0 |
| pi | union-alpha | high | feature | 217.9 | 10 | 31149 | 7725 | 179724 | 218598 | $0.0000 | 12 PASS | 8 PASS | ok | exit 0 |
| pi | union-alpha | off | feature | 92.6 | 7 | 60549 | 2011 | 73904 | 136464 | $0.0000 | 12 PASS | 5 PASS | ok | exit 0 |
| pi | union-alpha | off | refactor | 114.2 | 6 | 25967 | 3600 | 96220 | 125787 | $0.0000 | 10 PASS | 3 PASS | ok | exit 0 |

## Aggregate per arm × model × thinking

| Arm | Model | Thinking | Tasks passed | Wall s (sum) | Wall s (median) | Total tokens | Input | Output | Cost | Model mismatch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pi | deepseek-flash | high | 3/3 | 75.2 | 23.2 | 594498 | 43168 | 11938 | $0.0305 | no |
| pi | deepseek-flash | low | 3/3 | 52.3 | 14.3 | 443763 | 41381 | 7758 | $0.0241 | no |
| pi | union-alpha | high | 1/1 | 217.9 | 217.9 | 218598 | 31149 | 7725 | $0.0000 | no |
| pi | union-alpha | off | 2/2 | 206.8 | 114.2 | 262251 | 86516 | 5611 | $0.0000 | no |

## Harness headline (all models and levels together)

| Arm | Trials | Acceptance | Wall s (sum) | Wall s (median) | Total tokens | Input | Output | Cost | Scope violations | Deadlines |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pi | 9 | 9/9 | 552.1 | 24.6 | 1519110 | 202214 | 33032 | $0.0546 | 0 | 0 |

## Same-model pairing (Pi minus OMP)

| Model | Thinking | Task | Acceptance (Pi/OMP) | Wall s (Pi/OMP) | Tokens (Pi/OMP) | Cost (Pi/OMP) |
| --- | --- | --- | --- | --- | --- | --- |

## Reliability — the headline finding

`stealth/union-alpha` is served by OpenRouter's anonymous stealth provider. Under the MEGAI Pi
profile it fails mid-run far too often to be used as a worker:

- OpenRouter answers the failing requests with HTTP 200 and a body error
  `{"message": "ERROR", "code": 502, "metadata": {"error_type": "provider_unavailable"}}` (captured
  with a direct API call, not inferred). Pi surfaces it as an assistant turn with
  `stopReason: "error"`, `errorMessage: "ERROR"` and zero usage.
- The profile disables provider retries (`settings.json`: `retry.enabled: false`,
  `retry.maxRetries: 0`), so a single 502 ends the trial.
- Direct 12-request sequential probe against the same model (68KB payload, ~4-5k tokens): **2/12
  (17%) failed** with `provider_unavailable`; the failures took 45.3s and 44.7s, successes
  2.8-20.2s.
- Harness attempts: union-alpha ran **11 times and completed 3** valid trials; `bugfix` never
  completed (6 runs: 5 at `high`, 1 at `off`). `deepseek-flash` ran 6 trials, all valid, with zero
  provider errors.
- Size is not the trigger: a 105KB payload failed once, then 17KB/34KB/51KB/68KB/85KB payloads
  succeeded, and a repeated identical 68KB request recovered immediately after a failure. The
  failures are sporadic upstream errors, not a request-shape or context-limit defect.

## Method caveats

- `union-alpha` exposes no reasoning control (`supported_parameters`: `max_tokens`,
  `response_format`, `temperature`, `tool_choice`, `tools`, `top_p`); Pi accepts `--thinking high`
  for it but sends nothing reasoning-related, and every union-alpha trial reports 0 reasoning
  tokens. The `Thinking` column records the *requested* level, and `off` cells were run to label
  this honestly.
- `deepseek-flash` levels here are `high` (planner) and `low` (scout/worker per `megai-roles.json`).
  The earlier pilot used `high`/`medium`, so cross-pilot deltas are indicative only.
- The `refactor` acceptance suite **passes on the pristine baseline** (`unittest discover` on the
  untouched `095a664e` checkout prints `OK`), so for that task acceptance cannot discriminate a
  no-op. Its PASS claims here are backed by a non-empty candidate diff (`union-alpha` off: 4299
  bytes; deepseek rows: present). `bugfix` and `feature` acceptance fail on the pristine baseline
  (2 failures / 18 errors), so those cells do discriminate.
- Baseline `095a664e` was supplied as a linked `git worktree`; trial clones are `cp -Rc` copies, so
  they shared that worktree's git dir and index. Every published record's `changed_paths` was
  re-checked against `allowed_paths` with no phantom path, and acceptance/participant results were
  re-run from the candidate files for all nine valid trials. A full clone remains the cleaner
  baseline for future runs.
- The backend footer aggregates all valid trials into `9/9 acceptance`; that count includes three
  union-alpha cells only because the provider-failed cells are excluded by the harness `valid`
  rule. Per-model completion is in the reliability section above.
- One run per cell remains an exploratory pilot; no significance claim is made.

## Verification

`verification.log` (private evidence directory) records: usage/request counters recomputed from the
raw harness streams for all 12 published records (exact, after the documented 1e-6 cost rounding);
`changed_paths` subset of `allowed_paths`; reported model id equal to the requested model; and an
independent re-run of both suites from the candidate files for all nine valid trials, agreeing with
every published acceptance and participant result.
