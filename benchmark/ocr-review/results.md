# OCR delegation vs current Pi reviewer — pilot result

**Decision: do not integrate OCR delegation into the current review workflow.**
The predeclared benefit threshold was not met. This says nothing about the
performance of OCR's native `review` engine, which was not tested.

## Paired result

One independent native Pi session per arm, each reviewing the same four frozen
cases in order b, d, a, c. Both used `openai-codex/gpt-5.6-sol`, thinking `high`,
with native model/thinking records verified before task dispatch. The brief,
source, output schema, and read-only boundaries were identical; OCR selection
and matched rules were the treatment. No answer-key access appeared in either
tool trace. Both sessions ran concurrently on the same host.

| Metric | Baseline Pi | Pi + OCR delegation | OCR difference |
| --- | ---: | ---: | ---: |
| Defective cases flagged | 3/3 | 3/3 | Same |
| Correct control judged clean | 1/1 | 1/1 | Same |
| Valid grouped findings | 4 | 4 | Same grouping |
| Observed false findings | 0 | 0 | Not a population rate |
| Frozen primary repro scenarios explicitly described | 2/3 | 3/3 | See nuance below |
| Wall time, task message to final response | 95.211 s | 152.412 s | +60.08% |
| Model requests | 8 | 20 | +150.00% |
| Total reported tokens, including cache reads | 266,104 | 560,795 | +110.74% |
| Uncached input tokens | 50,789 | 39,924 | Lower with OCR |
| Cached input tokens | 211,456 | 515,456 | Higher with OCR |
| Output tokens | 3,859 | 5,415 | Higher with OCR |
| Reported model cost | $0.475443 | $0.619798 | +30.36% |

Reported cost is Pi's model-priced usage, **not a verified bill or incremental
subscription charge**. Reasoning is already represented in the reported output/
total counters and is not added again. Task measurements exclude the neutral
READY exchange, installation, fixture preparation, parent orchestration and
scoring. They include all review tool/model turns, not just the final answer.

### Quality nuance

Both arms found missing readback-field validation, incorrect relationship-ID
normalization, ignored pagination signals, and unbound Git-index snapshots.
OCR explicitly described the terminal-page/stale-cursor scenario from the
frozen case-a reproduction. The baseline instead demonstrated another real
pagination failure: a declared next page without a cursor is silently accepted.
Thus case-level detection was equal, but primary-repro coverage was not identical.
Neither arm produced a false alarm on the behavior-preserving control.

The extra pagination and relationship findings were verified against base and
candidate code by the parent; they were not falsely marked as false positives
merely because the initial answer key omitted those scenarios. Four grouped
findings is not an exhaustive count of all independently triggerable bugs.

## Decision against the predeclared rule

The Plane item recorded the decision rule before execution: no lost known-defect
coverage or extra false positives, plus either >=20% fewer tokens or less wall
time, or additional validated material defects without >20% token/time regression.
OCR gave more explicit coverage of one pagination scenario, but both time and
tokens regressed beyond that ceiling. **No adoption signal in this pilot.**
No live Pi skill, profile, mandatory review stage, provider, or CI integration
was installed. OCR exists only inside this isolated task's ignored tools folder.

## Provenance and verification

- Plane: MEGAI-107; task `93108708-9d92-40e4-a3f4-7637bf88ecd1`.
- Fixture commit: `a29a98b21a09f9e889d58b1c41c56deaf3331f3e`.
- Task branch: `task/ocr-review-benchmark`, dev base `0d0428d`.
- OCR: `1.12.4`, native build `f1101fd7f`, darwin/arm64.
- Binary SHA256: `b2944c8823075fd4edbedf521956d4893b4e973e5d47ed12f2f223cd21e792db`.
- Baseline session: `01a0ab0f-ff80-7774-a148-9e6cf01de365`.
- OCR session: `01a0ab0f-ff6c-777c-8f8c-29c477f16928`.
- Four snapshot files byte-match their stated historical MEGAI source commits.
- Red/green checks: each defect fails on candidate and passes on base; control
  passes both. Parent inspected actual checks and raw outputs.
- Parent verified all 14 frozen checksums before and after review, unchanged
  case refs/clean case worktrees, binary version/checksum, and Ruff PASS for
  the new fixture-preparation and private-verification Python scripts.
- Private durable evidence: `~/.megai/evidence/megai-107-ocr-review/`, containing
  native sessions, task-only metrics, final findings, ground truth, red/green
  checks/logs, extra-findings verification, and post-review integrity results.

## Preparation overhead and limits

The DeepSeek-low fixture worker consumed 78 requests, 5,705,091 reported total
(replayed/cached included) tokens and $0.1176759 reported cost, including its
READY exchange. Each reviewer READY exchange separately used 17,244 tokens and
$0.086345. Parent coordination/scoring is not included in those figures; these
are **not a complete end-to-end experiment cost** or a workflow-wide savings claim.

This is one four-case paired pilot, not repeated or statistically conclusive.
The inputs are narrow, single-file Python reversions of real MEGAI fixes plus
one seeded clean refactor; they do not test large/multifile reviews, other
languages, configurable custom rule sets, or the native OCR agent's reflection/
positioning machinery. All cases share one session per arm, so costs are batch
measurements and case contexts are not independent trials. Live shared-host load,
provider latency/cache state, ordinary model variability and differing tool use
can affect timings. Cache was measured, not experimentally controlled.
The result supports **keeping the current workflow for now**, not declaring OCR
universally worse. No optional follow-up runs or integration were performed.

## Delivery boundary

Research artifacts are retained on the isolated task branch. The primary dev
checkout has unrelated uncommitted benchmark work, so it was left untouched;
no dev/main merge or push was performed. Private evidence is preserved outside
the worktree. The task remains a reviewed research handoff, not a main-delivered
product change.
