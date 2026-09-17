# Local Qwen3.8-35B-A3B-Distill mixed with deepseek-flash — results

Measures what a self-hosted model adds to the paid worker. The request was
*"how much advantage does the local Qwen give when used mixed with deepseek"*, so
the mixed setup is modelled as the MEGAI pattern: a worker writes the change, a
paid reviewer checks it.

Arms, all on the frozen `capy` exercises, Pi harness, one run per cell:

| Arm | `--arm` | Worker | Reviewer |
| --- | --- | --- | --- |
| deepseek alone | `pi` | `deepseek/deepseek-flash` | none |
| local alone | `pi` | `qwen38-local/qwen3.8-35b-a3b-distill` | none |
| **mixed** | `hybrid` | `qwen38-local/qwen3.8-35b-a3b-distill` | `deepseek/deepseek-flash` |
| review control | `hybrid` | `deepseek/deepseek-flash` | `deepseek/deepseek-flash` |

Baseline `095a664e` | 12/12 valid | all four arms asked for `high` thinking.

## Headline

**Mix quality is identical here, and mixing is not where the saving is.** All 12
trials passed the frozen acceptance suites, every worker passed its own acceptance
*before* the reviewer ran (6/6 mixed trials), and no reviewer changed a line of
code in 6/6 mixed trials.

| Arm | Trials | Acceptance | Wall s (sum) | Wall s (median) | Uncached input | Output | Cache read | Reported cost | Cost per task |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pi` + deepseek-flash (worker only) | 3 | 3/3 | 90.4 | 28.1 | 49953 | 14996 | 675584 | $0.03703 | $0.01235 |
| `pi` + qwen38-local (worker only) | 3 | 3/3 | 694.1 | 213.2 | 71848 | 18765 | 868994 | $0.00000 | $0.00000 |
| `hybrid` + qwen38-local (qwen worker -> deepseek reviewer) | 3 | 3/3 | 426.7 | 143.7 | 122724 | 20948 | 836075 | $0.03370 | $0.01123 |
| `hybrid` + deepseek-flash (deepseek worker -> deepseek reviewer) | 3 | 3/3 | 141.9 | 38.3 | 62189 | 24768 | 985344 | $0.05429 | $0.01810 |

Per task, the mixed arm costs about the same as letting deepseek do the work alone:

| Task | deepseek alone $ | qwen alone $ | qwen worker + deepseek reviewer $ | deepseek worker + deepseek reviewer $ | deepseek alone s | qwen alone s | qwen + deepseek s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| bugfix | $0.00922 | $0.00000 | $0.01071 | $0.01341 | 21.2 | 270.4 | 143.7 |
| feature | $0.01173 | $0.00000 | $0.01006 | $0.01580 | 28.1 | 213.2 | 123.1 |
| refactor | $0.01609 | $0.00000 | $0.01293 | $0.02508 | 41.0 | 210.4 | 159.9 |

- **Cost: mixed ≈ deepseek alone** — $0.01123 vs $0.01235 per task, 9% cheaper on
  three tasks (inside single-run noise). The reason is that the review stage is not
  cheap: review-only runs cost $0.00480 / $0.00728 / $0.00671, so the review stage
  alone is 42–62% of a full deepseek run. Deepseek's prompt cache makes
  "just do it yourself" nearly as cheap as "check someone else's work".
- **Wall time: mixed is 4.7× slower** — 426.7 s vs 90.4 s total, median 143.7 s vs
  28.1 s per task. The worker is the whole cost: local decode is ~47 tok/s.
- **Local alone is the only real saving** — $0.00000 per task with the same 3/3
  acceptance, at 5–13× the wall time (210–270 s versus 21–41 s; 7.7× in total).

So the advantage of the local model is **not** in a worker+reviewer mix, where the
paid review absorbs almost all of the money it saves. It is in work whose acceptance
is already machine-checkable: there the local model costs nothing and needs no paid
reviewer at all, which is exactly the 3/3 at $0.00000 in the `pi` + qwen row.

## Per-trial results

| Arm | Task | Worker s | Reviewer s | Total s | Worker $ | Reviewer $ | Total $ | Worker acceptance | Reviewer code change |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `pi` + deepseek-flash | bugfix | 21.2 | n/a | 21.2 | $0.00922 | n/a | $0.00922 | pass | n/a (no review stage) |
| `pi` + deepseek-flash | feature | 28.1 | n/a | 28.1 | $0.01173 | n/a | $0.01173 | pass | n/a (no review stage) |
| `pi` + deepseek-flash | refactor | 41.0 | n/a | 41.0 | $0.01609 | n/a | $0.01609 | pass | n/a (no review stage) |
| `pi` + qwen38-local | bugfix | 270.4 | n/a | 270.4 | $0.00000 | n/a | $0.00000 | pass | n/a (no review stage) |
| `pi` + qwen38-local | feature | 213.2 | n/a | 213.2 | $0.00000 | n/a | $0.00000 | pass | n/a (no review stage) |
| `pi` + qwen38-local | refactor | 210.4 | n/a | 210.4 | $0.00000 | n/a | $0.00000 | pass | n/a (no review stage) |
| `hybrid` + qwen38-local | bugfix | 120.7 | 22.7 | 143.7 | $0.00000 | $0.01071 | $0.01071 | pass | none |
| `hybrid` + qwen38-local | feature | 101.0 | 21.8 | 123.1 | $0.00000 | $0.01006 | $0.01006 | pass | none |
| `hybrid` + qwen38-local | refactor | 133.0 | 26.7 | 159.9 | $0.00000 | $0.01293 | $0.01293 | pass | none |
| `hybrid` + deepseek-flash | bugfix | 17.9 | 16.8 | 34.9 | $0.00861 | $0.00480 | $0.01341 | pass | none |
| `hybrid` + deepseek-flash | feature | 17.9 | 20.2 | 38.3 | $0.00852 | $0.00728 | $0.01580 | pass | none |
| `hybrid` + deepseek-flash | refactor | 47.7 | 20.8 | 68.7 | $0.01837 | $0.00671 | $0.02508 | pass | none |

`Worker acceptance` is the acceptance suite run against the worker's diff *before*
the reviewer touched it. `Reviewer code change` compares the two diffs ignoring
`__pycache__`.

- Worker acceptance before review: **6/6** in the mixed arms, and each single-model
  arm also passed its own acceptance.
- Reviewer code change: **0/6** — reviewers read the diff, ran the suite and stopped.
- One trial (`hybrid` + deepseek-flash, refactor) reports `scope_ok: false` only
  because running the suite wrote `capy/benchmark/cases/refactor/__pycache__/*.pyc`;
  the code-only diff is byte-identical to the worker's, and no source file outside
  the two allowed paths was touched.

## Where the difference actually comes from

| Effect | Measured |
| --- | --- |
| Worker quality gap on these tasks | none observable (all workers passed) |
| Reviewer value added | none observable (0/6 code changes) |
| Review stage cost | $0.00480–$0.01293, ≈ half a full run |
| Local worker cost | $0.00000 in API terms |
| Local worker wall time | 101–133 s in the mixed arms, 210–270 s alone |
| Paid worker wall time | 18–48 s |

## Limits

- Three small frozen exercises (one file each, public seam) and one run per cell.
  n=3 per arm: differences of one dollar-cent or one task are noise, and no
  repeatability was measured.
- Acceptance is the only quality signal. An exercise this small cannot show the
  quality gap that a 3B-active distilled model would eventually show on a large,
  ambiguous change; these results do not claim local quality parity in general.
- The local arm's thinking level is not Pi-controlled: the server runs with
  `--reasoning on`, and the `qwen38-local` provider sets
  `compat.supportsReasoningEffort: false`, so the requested `high` level is ignored
  and the recorded level is nominal.
- Cost is the provider's reported number. The local arm's API cost is $0 but it
  occupied a 12 GB GPU for every one of those minutes; that is not priced here.
- The reviewer re-establishes full repository context (it re-reads files and runs
  the suite), so these review costs are not the cost of a diff-scoped review.
- Local runs cross a Tailscale link to a second machine, so their wall time includes
  network round trips, not only inference.

## Environment

| Item | Value |
| --- | --- |
| Server | `llama-server` 0.4.1-dev (build 11016, CUDA 13.3) on Arch/Omarchy |
| Model | `Qwen3.8-35B-A3B-Q4_K_M.gguf`, SHA256 verified against the publisher |
| Flags | `-ngl 99 --n-cpu-moe 30 --load-mode none -c 262144 -fa on --jinja -np 1 --cache-type-k q8_0 --cache-type-v q8_0 --reasoning on` |
| Host | RTX 3060 12 GB, 31 GB RAM, 20 threads; MoE experts split to CPU |
| Pi provider | `qwen38-local` → OpenAI-compatible `http://<tailnet>:8080/v1` |

## Evidence

- Private (`--root`): raw harness JSON streams, per-trial prompts, `worker.diff` /
  `candidate.diff`, evaluation output and per-trial checkouts for all 12 trials.
- Published: this file and `qwen-hybrid.trials.json` (12 records, one per trial id,
  no raw provider payloads, no credentials).
- Reproduce the mixed arm:

```sh
python3 benchmark/pi-vs-omp/run_bench.py trial \
  --arm hybrid --model qwen38-local/qwen3.8-35b-a3b-distill --thinking high \
  --task bugfix --baseline BASELINE --root DIR --results DIR/trials.jsonl --budget 1800
```
