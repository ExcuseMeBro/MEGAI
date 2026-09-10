# Capy vs Pi + MEGAI: isolated benchmark

Protocol draft only: no fixtures, tests or measured runs exist yet. Approve the
three public interfaces in [tasks.md](tasks.md) before tests are written. This is
a small Python coding smoke benchmark, not evidence about large-repository work,
UI quality, security work or general model superiority.

## Comparison arms

- **Pi + MEGAI:** fresh Pi session, exact `openai-codex/gpt-6-astra`, effective
  thinking `high`; record the active MEGAI resources rather than assuming them.
- **Capy + MEGAI Lite:** a fresh Capy session with GPT-6 Astra and high thinking,
  supplied with the frozen version of [the instructions pack](../instructions.md).
  This is not a stock-Capy comparison. Record the model identifier exposed by
  Capy; if only a display label is available, exact backend parity is unverified.

The user runs Capy manually. The coordinator never launches a non-Pi agent or
copies credentials between hosts. A verified Pi child runs each Pi task; the
fixture author does not solve it in the authoring session. If a fresh approved
Pi session is unavailable, report the blocker rather than substituting a model.

## Freeze before execution

1. Approve the public interfaces, then build three independent fixture directories
   and standard-library `unittest` suites. No network, installs or production data.
   Pin the same available Python minor version in both environments and record
   OS, Python patch version and installed tools. If they differ, disclose it.
2. Verify the bugfix and feature fixtures fail their intended acceptance cases,
   not imports or environment setup. Verify the refactor fixture passes its full
   characterization suite. Check that deliberately incorrect output makes each
   suite fail. Inspect expected values against the approved contracts.
3. Freeze a baseline commit, fixture hashes, acceptance-suite hashes and one
   exact prompt per task. Make the same tests visible to both participants;
   retain a read-only evaluator copy outside either writable checkout. No hidden
   requirements. Baseline commit is assigned after fixtures exist, not this draft.
4. Give each arm an independent clean copy from that baseline and allow writes
   only to the assigned implementation and participant-owned test file. Preserve
   the frozen acceptance tests. No solution, transcript or feedback crosses arms.
   Both arms receive the same task wording, paths, acceptance and budget; record
   differing host instructions/tools as the intended configuration difference.
5. Plane remains the sole execution tracker. The parent retains one benchmark
   item and records slice acceptance; benchmark participants are leaf workers
   and do not mutate Plane, delegate, commit, push or merge. Thus these timed
   coding trials do **not** score autonomous Plane/task-flow behavior.

## Run and record

For each task, use new sessions in both arms and alternate which arm runs first
across tasks. Verify model/thinking before sending task context. Record setup time
separately; start task elapsed time when the complete task prompt is submitted.
Include model/tool waits and any repair prompts. Capture elapsed time when the
participant returns its final diff or five-minute checkpoint. At 300 seconds,
checkpoint; preserve any in-flight non-interruptible write and record an overrun
rather than killing it or reporting it as a fast completion. Stop the trial there.

Export the candidate diff, raw commands/test logs, timestamps, visible usage and
human interventions without secrets or unrelated session content. Evaluate the
captured candidate using the frozen suite in a separate clean copy. Report
participant wall time and evaluator time separately; a quick answer that fails
acceptance is not a faster successful result. No unreported retries. Any later
repair is a separate labeled follow-up, not a replacement for the first result.

Record these fields per task and arm (unknown values are `null`, never zero):

| Field | Evidence |
| --- | --- |
| task / arm / baseline / prompt hash | Frozen input identity |
| model / thinking / environment | Host status or redacted screenshot |
| setup / task / evaluation seconds | Timestamp differences and clock source |
| acceptance passed / total / exit status | Raw evaluator output |
| input / output / cached tokens | Host-reported counters, with metric definitions |
| reported cost / currency / billing basis | Actual host billing; separate subscription attribution |
| interventions | Count and content of human repair/clarification prompts |
| scope compliance | Full diff and frozen-file hashes |
| review findings / severity | Path-and-line findings, not line-count scoring |
| stop reason | Returned result, deadline, model error or environment blocker |

A model/permission failure stays in the results. Follow the host's escalation
policy for recovery, but a different-model recovery is excluded from this
same-model comparison and reported separately. Never expose credentials in logs.

## Judge and stop

Run identical acceptance tests first. Review anonymized A/B diffs for contract
violations, scope drift, readability and unnecessary dependencies; acknowledge
that manual review is subjective. Preserve raw failures. Review tooling and local
Ruff checks run in the evaluator, outside the participant timing, for both arms.

Publish per-task results before any summary. Report successful tasks out of three,
then elapsed time and available cost for passing results; retain failed and timed
out trials in the table. Do not rank by speed alone, infer missing cost from token
counts, or treat changed-line counts as quality. One run per task is an exploratory
pilot; repetitions require additional explicit user scope. Report environment and
model-parity limitations and avoid a universal winner from three small exercises.

Store sanitized measurement artifacts here only after real runs. Task execution
status stays in Plane. Benchmark output is not automatically merged into MEGAI's
production code; preparation documents are delivered only to `capy`.
