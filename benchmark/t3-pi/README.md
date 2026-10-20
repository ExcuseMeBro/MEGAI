# T3-style receipts around Pi: measured feasibility study

Research only, 2026-10-20, Plane **MEGAI-219**. This directory is opt-in: nothing
imports it into Pi, changes settings, or installs production orchestration.

## Answer

**Yes, adapt the orchestration principles, not the entire T3 server.** A Pi RPC/SDK
adapter can retain the selected provider/model/thinking while a small outer layer
owns command identities, durable receipts/events and recovery policy. The measured
benefit here is **avoiding completed command replay**, not faster model reasoning,
better code, automatic Git reconciliation, or exactly-once external side effects.

A complete port is **not implemented or benchmarked** here. `bench.py` is an original,
small SQLite receipt experiment, not T3's production orchestrator. It intentionally
has no provider normalizer, event projection, outbox worker, approval system,
root/child execution graph, migrations, retention, cancellation, source-pinned
acceptance, multi-repo delivery or production security boundary.

## Pinned source inspection

T3 source: [`67c0fc0cdaf963b103518862dd7b68a9c758ecf2`](https://github.com/pingdotgg/t3code/tree/67c0fc0cdaf963b103518862dd7b68a9c758ecf2).

* [`Orchestrator.ts:11437–11494`](https://github.com/pingdotgg/t3code/blob/67c0fc0cdaf963b103518862dd7b68a9c758ecf2/apps/server/src/orchestration-v2/Orchestrator.ts#L11437-L11494):
  looks up an existing command receipt, rejects an incompatible thread, and returns
  stored events/sequence instead of redispatching the command.
* [`Orchestrator.ts:11628–11648`](https://github.com/pingdotgg/t3code/blob/67c0fc0cdaf963b103518862dd7b68a9c758ecf2/apps/server/src/orchestration-v2/Orchestrator.ts#L11628-L11648):
  keyed thread dispatch locks; some child intake also takes the parent lock.
  This is not one global lock around all implementation work.
* [`EventSink.ts`](https://github.com/pingdotgg/t3code/blob/67c0fc0cdaf963b103518862dd7b68a9c758ecf2/apps/server/src/orchestration-v2/EventSink.ts):
  transactions coordinate domain events, projections, receipts and effect-outbox
  enqueue. A transaction does **not** make a remote provider or Git push atomic.
* [`ProviderRuntimeRecoveryService.ts:527–555`](https://github.com/pingdotgg/t3code/blob/67c0fc0cdaf963b103518862dd7b68a9c758ecf2/apps/server/src/orchestration-v2/ProviderRuntimeRecoveryService.ts#L527-L555):
  recovery ends orphaned native subagents/root turns. Recovery is policy, not a
  guarantee that every interrupted operation seamlessly resumes.
* [`testing-strategy.md`](https://github.com/pingdotgg/t3code/blob/67c0fc0cdaf963b103518862dd7b68a9c758ecf2/docs/orchestration-v2/testing-strategy.md):
  recommends real orchestration/persistence with replay only at external boundaries.
  **This benchmark does not run those upstream integration tests.**
* [`LICENSE`](https://github.com/pingdotgg/t3code/blob/67c0fc0cdaf963b103518862dd7b68a9c758ecf2/LICENSE):
  MIT, copyright T3 Tools Inc. Any later copied/substantial upstream code must retain
  its license notice. This experiment does not copy upstream implementation.

Installed Pi 1.3.0 RPC accepts a correlation `id`; replaying the same `bash` command
id actually executes it again. A persisted Pi session is conversation history,
not an application command-receipt ledger. This was verified by execution, including
reopening a real persisted Pi session, not inferred from documentation alone.

## Reproduction

Python 3.14.6, Node v24.18.0, Pi 1.3.0, macOS arm64. Dependencies: stdlib Python,
installed `pi` and its existing authentication. No packages are installed.

```sh
cd benchmark/t3-pi
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_bench
python3 -B bench.py --out /absolute/new/disposable/smoke --smoke --live 1
python3 -B bench.py --out /absolute/new/disposable/run --repeats 20 --live 3
```

`--out` must not exist. `--live 0` (default) runs real Pi RPC/local bash tests without
model requests. `--live 3` adds **billable/model-backed** coding trials. Paths must be
private, disposable and outside production checkouts. Do not expose the RPC pipe:
Pi RPC intentionally allows shell commands; this is not a sandbox. Deadlines are
bounded; timeout/error retains evidence and never signals an existing user session.

Both variants use the same actual Pi executable with `-ne -ns -np --no-themes`.
Those flags disable extensions/skills for a controlled RPC comparison. **This is
not an end-to-end benchmark of the complete MEGAI production harness or T3 UI.**
No provider, model, thinking or authentication override is passed. All six coding
sessions reported `openai-codex / gpt-6.1-sol / medium`.

Raw sanitized measurements: [`results-2026-10-20.json`](results-2026-10-20.json).
The run started at `2026-10-20T12:43:10Z`. Full private session/fixture artifacts are
retained separately, not committed; results contain only timings/counts/usage and
model identity, not credentials or private prompts.

## Real local RPC/fault results

Effects are appended lines in disposable files. These are actual Pi-executed shell
side effects; they are **not model calls**. Latencies exclude process startup except
the explicit restart scenario. The first two modes are run in blocks; OS-cache and
ordering noise are uncontrolled, so millisecond differences are descriptive only.

| Scenario | Trials/variant | Plain Pi effects | Receipt variant effects | Key observation |
|---|---:|---:|---:|---|
| Normal, one command | 20 | 20 | 20 | Median 3.617 vs 4.476 ms; persistence adds work |
| Same id delivered 3 times | 20 | 60 | 20 | Completed duplicates eliminated |
| Caller loses ack after receipt commit; ledger reopened | 20 | 40 | 20 | Completed receipt survives reopen |
| Caller loses result before receipt commit | 20 | 40 | 20 | Prototype blocks **20/20** retries as uncertain |
| Natural EOF/reopen of real persisted Pi session | 5 | 10 | 5 | Session history alone does not deduplicate ids |
| Two independent Pi clients running in parallel | 10 | 20 | 20 | Median batch 240.097 vs 247.489 ms; no parallel speedup shown |

Additional prototype-only concurrency invariant: two controllers racing one id,
20 trials, exactly one Pi execution each; the other caller is blocked while the
result is in flight. Plain concurrent same-client bash is not used as a fake
comparison; Pi does not promise that behavior.

Fault injection is at the **caller/receipt boundary**. The test recreates SQLite
connections, not a power failure or killed provider. The persisted-session test is
a **clean process restart**, not crash recovery. No existing user session, shared
queue grant, production branch or provider process was terminated for testing.

## Actual model-backed coding A/B

Three repetitions of **one small slug-function repair**, not three different
problems. Same starting files, prompt, external unittest check,
provider/model/thinking. Mode order alternates AB/BA/AB. Each condition deliberately
gets a duplicate of the *same command id* after completion. All first executions
passed the unchanged acceptance test: **3/3 plain, 3/3 receipt variant**. The second
attempt is checked again from disk, not trusted merely because a receipt exists.

| Measurement | Plain Pi | Receipt variant |
|---|---:|---:|
| First execution median | 20.998 s | 22.813 s |
| First execution individual times | 20.998 / 23.450 / 20.164 s | 29.211 / 22.813 / 22.237 s |
| Duplicate command response | 7.641 / 7.464 / 7.658 s | 0.386 / 0.442 / 0.427 ms |
| Actual prompt dispatches, including duplicates | 6 | 3 |
| Extra usage on duplicate attempts: uncached input | 10,910 tokens | 0 |
| Extra usage on duplicate attempts: output | 303 tokens | 0 |
| Extra usage on duplicate attempts: cache read | 27,904 tokens | 0 |
| Median first+duplicate pair | 28.639 s | 22.813 s |

No-fault first execution **did not get faster**. Three trials and one trivial task
cannot establish coding-quality, throughput, cost-per-real-task or normal-latency
improvements. Provider caching, variable model turns and service latency are not
controlled; total token differences between *first* executions are not attributable
to receipts. We do not convert token counts into money or claim a general speedup.
The paired workload intentionally has a 100% completed-duplicate rate: the saved
retry cost is real, but extrapolating its percentage to ordinary work would mislead.
Actual model requests may span several assistant/tool turns; the dispatch counts
above count **top-level prompts**, not HTTP/model round trips.

## What this buys this workflow

1. **Useful now, as a design:** stable command identities + durable receipts for
   retries/reconnects; explicit `accepted/running/completed/uncertain` states.
2. **Worth a guarded implementation next:** normalize Pi terminal events into a
   small run/attempt ledger; restore UI state from stored normalized events; add
   root/child correlation only when a real subagent runtime supplies those ids.
3. **Keep existing authority:** Plane owns task acceptance; source-current tests,
   reserved shared delivery, exact local/remote inclusion checks and safe cleanup
   remain authoritative. A successful model turn is not delivered Git work.
4. **Do not port blindly:** no global implementation queue, background agent fleet,
   provider switching, new UI or replacement for the existing Git task runner.
   T3 orchestration alone does not fix worktree cleanup or a diverged branch.

Production delivery would need a separate frozen safety/acceptance gate: WAL/schema
migration/retention, per-thread concurrency, cancellation semantics, partial event
replay, source/current receipt validation, existing grants, provider interruption,
approvals and exact external-effect reconciliation. In particular, a side effect
can complete before a receipt commits: this experiment honestly **stops and asks
for reconciliation**, including a conservative block even if failure happened
before send. It does not solve exactly-once execution or eliminate all manual work.
