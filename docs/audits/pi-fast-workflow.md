# Pi fast-workflow audit — MEGAI-60 r2

Scope: three retrospective real repository tasks (`provider-progress-58`,
`megai-59`, `megai-60`), one observed redundant environment-check exchange
from a separate MEGAI60 Sol reviewer neutral session, and the current MEGAI-60
r2 MiniMax writer startup captured from native records. This documents what
those observations actually show and what they do **not** prove. It is not a
controlled benchmark, a synthetic cross-parent comparison, a latency/quality
guarantee, or a claim that the new routing will speed up tasks.

**Caveat on the all-GPT sample telemetry.** Tasks 58 and 59 both predate the
`economy` preset rollout; the `economy` preset was installed only at the end
of task 60. Their GPT-only telemetry is therefore **not** evidence that the
already-installed `economy` policy failed or regressed. Those samples simply
show what was running before the preset existed. The concrete inherited-parent
observation that this audit actually targets is the current session: a Paseo
Pi tab on `openai-codex/gpt-6-astra`/`high` while the local `megai-roles.json`
already says `economy` and the installed `settings.json` defaults are
`minimax`/`MiniMax-M3`/`high`. The routing refinement addresses that
inherited/pinned-session distinction, not a measured before/after speed
regression.

The frozen sanitized metrics live at
[`docs/audits/pi-task-sample.json`](pi-task-sample.json) (byte-equal to the
private input, verified by SHA-256 in tests). Per-task source locations and
event boundaries are recorded in the private acceptance folder; the in-repo
copy only carries the redacted numbers, hashes and limitations.

## What the three retrospective samples actually show

| Metric (parent only) | provider-progress-58 | megai-59 | megai-60 |
| --- | --- | --- | --- |
| Sample kind | retrospective real repository task | retrospective real repository task | retrospective real repository task |
| Start / end event IDs | `837b6131` / `fb6ef3f0` | `a2ba02b1` / `cb395527` | `f9abe5fa` / `a139f3e1` |
| Interval seconds | 2040.109 | 1306.661 | 1676.019 |
| Single-task wall seconds | unknown (interval also covers task57) | 1306.661 | 1676.019 |
| Parent assistant messages | 63 | 69 | 94 |
| Parent usage messages | 63 | 69 | 94 |
| Parent input tokens | 72798 | 281455 | 341752 |
| Parent output tokens | 37976 | 20912 | 36866 |
| Parent cacheRead tokens | 9264640 | 6173056 | 8902272 |
| Parent cacheWrite tokens | 0 | 0 | 0 |
| Parent totalTokens | 9375414 | 6475423 | 9280890 |
| Parent model | openai-codex/gpt-6-astra ×63 | openai-codex/gpt-6-astra ×69 | openai-codex/gpt-6-astra ×94 |
| Parent tool calls | mcp 19, bash 29, write 5, edit 6, read 21 | read 35, bash 39, headroom_memory 1, mcp 47, write 5, edit 3 | read 26, bash 38, mcp 38, headroom_memory 1, write 11, edit 25 |
| Final verification seconds | 6.622989 | 59.180613 | 27.838327 |
| Independent final verdict | PASS | PASS | PASS |

Final verification sums the per-check `duration_seconds` from the accepted
candidate receipts only. They exclude earlier failing attempts: task58 candidate1
was BLOCKED by the native-safety check and is not part of any total; task59
retained a preexisting policy-wording failure that was fixed in the concurrent
MEGAI-60 candidate; task60 first reviewer found two defects that the parent
reproduced and fixed, and only the fixed candidate produced the `PASS` evidence
above.

## Honest unknowns and limitations

The dataset cannot tell us:

- **Task58 single-task latency.** The recorded interval covers task57 plus the
  task58 work; the time spent on each is not separated.
- **Child token totals.** `child_usage` is `null` for all three samples. This
  means the metric was not attributed or collected for those sessions, **not**
  that zero children ran: all three tasks had independent reviewers, and task60
  also ran a MiniMax smoke check. The null fields are an unknown, not a zero,
  and no child attribution is being claimed.
- **Pause subtraction.** Idle time, provider waits and tool timeouts are not
  removed; `provider_wait_seconds` is `null` for every sample.
- **User intervention cost.** `human_interventions` is `null`; these samples do
  not measure user message frequency or duration.
- **Cross-model quality.** Every measured parent ran GPT (`openai-codex/gpt-6-astra`).
  No MiniMax coding-quality conclusion can be drawn from these intervals; the
  new routing is policy, not a measured replacement of any model.
- **Causal speed or savings claim.** The samples are observations of three
  separate tasks under different conditions. They do not establish a before/after
  speedup, a quota saving, or a latency distribution. There is no synthetic
  other-parent benchmark substituted here: the new economy routing is asserted by
  policy text and tests, not by re-running these three tasks against MiniMax.

Cache counters (`cacheRead`) are reported separately from input tokens and
represent cache lookups rather than unique context tokens or billed cost.
`totalTokens` is the sum the provider surfaced; it is not a billed amount.

## One observed Sol reviewer env-check exchange — not a whole-task speedup

A separate neutral environment-check exchange on a Sol reviewer session was
captured (provider `openai-codex/gpt-5.6-sol`, thinking `high`). It was one
parent-chosen redundant prompt, not a recurring cost the prior policy would
charge on every fresh launch:

- Interval seconds: 5.287
- Assistant requests: 2
- Usage reported: input 8874, output 82, cacheRead 8448, cacheWrite 0,
  totalTokens 17404
- Matching native identity already present: `true` (a `model_change` to
  `openai-codex/gpt-5.6-sol` and a matching `thinking_level_change` to `high`
  were already on the session before the prompt was sent).

The prior delegation policy already allowed either the native metadata path
**or** the environment fallback. The new wording simply makes the existing
native-metadata path the preferred one when its records match the exact current
Paseo provider, model and thinking. The redundant exchange above shows the
cost of one parent-chosen fallback use on a session that already had matching
native records; it does **not** mean the prior policy would issue that prompt
on every launch, and it is not a whole-task speedup. The fallback prompt is
retained for sessions where the native records are missing, stale, ambiguous,
or come from a restored agent on a different branch.

## Current MiniMax writer startup — verified, not benchmarked

The current MEGAI-60 r2 MiniMax writer (`worker-native.json`) was captured
from native Pi records without any additional model-based environment prompt:

- Native session: `01a0964d-44e7-73f2-b198-5a3f744da6de`
- Paseo model: `minimax/MiniMax-M3`, effective thinking `high`
- `model_change` event: provider `minimax`, model `MiniMax-M3`
- `thinking_level_change` event: `high`
- `READY`: `true`
- Extra environment model prompts: `0`

This proves that, for this writer, the new policy path resolves the native
identity from existing records and does not issue the redundant second
prompt. It does not establish MiniMax availability for other sessions, nor a
quota saving, nor a latency target. Availability still has to be observed on
each fresh launch through the same native-record path.

## What this audit does and does not justify

- Documents three real retrospective intervals with reproducible per-sample
  metadata, including the SHA-256 of the merged event interval and of the final
  evidence file, so reviewers can verify exact numbers without leaking session
  contents.
- Lists the real limitations (parent-only usage with `null` children/pauses,
  all-GPT parents, failed-attempt exclusion) so the policy can be evaluated
  honestly.
- Records one Sol reviewer env-check exchange as the cost of one
  parent-chosen redundant prompt and reframes the writer startup as a verified
  native-resolution path, not a benchmark.
- Leaves the policy change itself to `pi-skill/ADAPTIVE.md` and
  `pi-skill/delegation.md`, where focused tests in
  `tests/pi_fast_workflow.py` lock down the routing, override, fallback and
  dataset contracts.