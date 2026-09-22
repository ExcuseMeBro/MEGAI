# Pi + MEGAI vs OMP + MEGAI — harness benchmark

Measures the two MEGAI harness profiles on identical frozen Python tasks and
reports speed, wall time, token consumption, reported cost and acceptance in one
table. Requested comparison: **Pi + MEGAI (`pi` branch)** against **OMP + MEGAI
(`omp` branch)** across DeepSeek and GPT models at high thinking and a second requested
level (`medium`, which DeepSeek Flash clamps — see the correction under Matrix).

## Arms and configuration identity

| Arm | Harness | MEGAI profile | Branch assertion |
| --- | --- | --- | --- |
| `pi` | `pi` 0.85.1 | `~/.pi/agent` (MEGAI Pi profile, `remove_omp` installer → `pi` branch) | Pi-only profile |
| `omp` | `omp/18.2.0` | `~/.omp/agent` (MEGAI `megai:slim` rules + `megai`, `megai-task-flow`, `agent-worktree-lifecycle` skills) | Profile that keeps OMP installed |
| `hybrid` | `pi` (two stages) | same as `pi` | Pi-only profile |

The two branches differ by one commit each from their common base: `pi` adds
Pi-side context/usage tooling, `omp` drops the Pi installer's OMP-removal path.
Because the `pi` branch installer would delete the OMP installation that the
other arm needs, both arms run with the locally installed MEGAI profile held
constant. The varied variable is therefore the harness (and its model/thinking
selection), which is the comparison the request asks for. This is recorded as a
limitation, not silently claimed as full branch isolation.

Native entry points only; no provider, credential, model or thinking rewriting:

- Pi: `pi -p --mode json --no-session -a --model MODEL --thinking LEVEL PROMPT`
- OMP: `omp -p --mode json --no-session --auto-approve --model MODEL --thinking=LEVEL PROMPT`

## Frozen inputs

Reused from the reviewed Capy preparation pack, not re-authored. That pack was
removed from the tree afterwards (Pi-only harness decision), so restore it from
the revision the trials ran against before rerunning:

```sh
git checkout caaf5e1 -- capy/
```

- Tasks and public seams: `capy/benchmark/tasks.md` (approved interfaces).
- Cases and acceptance suites: `capy/benchmark/cases/{bugfix,feature,refactor}/`,
  verified against `capy/benchmark/manifest.json` (11 files, no mismatches).
- Prompts: `prompts/{bugfix,feature,refactor}.md`, byte-identical apart from the
  task body and `{{MODEL}}`/`{{THINKING}}` placeholders; each trial records the
  resolved prompt hash.
- Baseline: the pinned clean checkout SHA recorded in every trial record and in
  the published result file.

The prompts and every trial record keep the original `capy/benchmark/...` paths,
so restored inputs must land back at those paths for a rerun to be comparable.

## Matrix

4 models × 2 thinking levels × 3 tasks × 2 arms = 48 trials, one run per cell.

- Models: `deepseek/deepseek-flash`, `openai-codex/gpt-6-astra`,
  `openai-codex/gpt-5.6-sol`, `openai-codex/gpt-5.6-luna`
- Thinking: `high`, `medium`
- Tasks: `bugfix` (defect fix), `feature` (implement `chunked`),
  `refactor` (de-duplicate `render_checks`)

**Correction (2026-09-16):** `medium` is not a DeepSeek Flash level. Its Pi model
store entry maps `minimal` and `medium` to `null`, so those trials sent no thinking
parameter at all and the DeepSeek comparison is `high` against none, not two levels.
GPT models are unaffected. See
[results/thinking-levels.md](results/thinking-levels.md), which reran the three tasks
at DeepSeek `low` and `high`, the levels that model actually accepts.

A model-comparison follow-up (`results/union-alpha.md`) adds
`openrouter/stealth/union-alpha` to `MODELS` and runs the Pi arm only
(`--arms pi`); its provider-failure evidence lives in the same file.

A local-model follow-up (`results/qwen-hybrid.md`) adds a self-hosted
`qwen38-local/qwen3.8-35b-a3b-distill` provider (a `llama-server` on the tailnet,
registered in `~/.pi/agent/models.json`) and a third arm, **`hybrid`**: the
`--model` value works the task first, then `HYBRID_REVIEWER`
(`deepseek/deepseek-flash`) reviews the uncommitted diff in the same trial checkout
using `prompts/review.md` and may fix it. Both stages are measured separately in
`stages`, the worker's own acceptance is evaluated before the reviewer runs, and
`reviewer_changed` compares the two diffs. Requires that provider to be reachable;
the other arms are unaffected. The reviewer model is selectable with
`--reviewer MODEL` (default `HYBRID_REVIEWER`) on both `trial` and `matrix`; a
non-default reviewer is part of the trial id, so both mixing directions can be
recorded in one results file.

A paid-model follow-up (`results/minimax-hybrid.md`) adds `minimax/MiniMax-M3` to
`MODELS` and runs all five arms — each model alone, both mixing directions, and the
deepseek/deepseek review control — to measure what the second paid model adds. It
is the same `hybrid` arm as the local-model run, only with a different worker and
reviewer.

Arm order alternates per task (Pi first for bugfix/refactor, OMP first for
feature) to reduce order bias. Trials run sequentially: concurrency would
confound the latency and token measurements this benchmark is about.

## Measurement

Per trial, timing starts when the complete prompt is submitted and stops when the
harness process exits, so model and tool waits are inside the wall time; setup
(repository clone, prompt rendering) is outside it. A 300-second budget applies;
an overrun is recorded as a deadline, never reported as a fast completion.

| Field | Evidence |
| --- | --- |
| Wall seconds | Monotonic clock around the harness process |
| Requests / turns | `turn_end` events in the harness JSON stream |
| Input / output / cache-read / total tokens, cost | Host-reported usage counters summed over requests |
| Reported models | Model id in each streamed assistant message (fallback detection) |
| Acceptance | Frozen suite re-run in a separate clean baseline copy in `eval/` |
| Participant tests | Participant-owned test file run separately, never mixed into acceptance |
| Scope | `git diff --name-only`, checked against the two allowed paths |
| Stop reason | Exit status, or `deadline` on the 300-second checkpoint |
| Baseline context | Trivial-prompt runs per arm (`overhead` subcommand) |
| Peak RSS, CPU seconds, page faults | `/usr/bin/time -l` around the harness process (`resources` subcommand) |

## Run

```bash
python3 benchmark/pi-vs-omp/run_bench.py overhead --root DIR --cwd BASELINE --reps 3
python3 benchmark/pi-vs-omp/run_bench.py resources --baseline BASELINE --root DIR --reps 2
python3 benchmark/pi-vs-omp/run_bench.py matrix \
  --baseline BASELINE --root DIR --results DIR/results.jsonl
python3 benchmark/pi-vs-omp/run_bench.py summarize \
  --results DIR/results.jsonl --root DIR --out benchmark/pi-vs-omp/results/summary.md
```

`--root` is a private evidence directory outside the repository: it holds the
trial checkouts, candidate diffs, raw harness streams, evaluation output and the
overhead runs. Only the sanitized records in `results/results.json` and
`results/summary.md` are published. `matrix` is resumable: recorded trial ids are
skipped.

## Limits

- One run per cell is an exploratory pilot, not a distribution; no significance
  claim is made from three small exercises.
- Reported cost is the harness's own estimate, not verified billing.
- Counter semantics are the harness-reported ones; the two harnesses agree on the
  JSON shape but are not independently reconciled against provider invoices.
- Acceptance covers the frozen contracts only. Readability, review quality,
  large-repository work, UI work and security work are out of scope.
- Pi's 180-second provider guard is part of the installed profile and stays
  active; a guard abort appears as a failed or truncated trial, not a retry.
