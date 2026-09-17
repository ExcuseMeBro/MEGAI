# TypeSafe agent skill — present vs absent on the three frozen MEGAI tasks

Profile comparison on the frozen fixtures: the same `pi` arm, the same
`deepseek/deepseek-flash` model, the same prompts, once with the TypeSafe agent
skill installed in `~/.pi/agent/skills/` and once with that directory parked. No
harness code and no other profile file changed, so the varied variable is the
skill and nothing else.

**No winner claim.** Every frozen acceptance suite passed in both states, so the
three exercises cannot separate them. What they can measure is the skill's
context cost, and that is the only number here with a clean signal.

## Headline: cost of having the skill available

Trivial-prompt runs (`overhead`, thinking off, 3 reps, same checkout). The total
context size is identical across the three reps of each state, so the difference
is not noise:

| Profile | Context tokens | Uncached input | Cache read | Rep 1 (cold cache) |
| --- | --- | --- | --- | --- |
| absent | 18,131 | 210 | 17,920 | 9,810 in / 8,320 cache |
| present | 18,302 | 253 | 18,048 | 9,853 in / 8,448 cache |
| delta | **+171 (+0.94%)** | +43 | +128 | +43 in / +128 cache |

The skill is loaded by progressive disclosure, so its presence costs one
name-plus-description entry in the system prompt on every request: **+171
tokens** here, split as +43 charged input and +128 absorbed by the prompt cache.
The ~10 KB `SKILL.md` body is only paid for if the agent opens it, and on these
tasks it did not.

## Matrix: 6 cells, both states

`pi` arm, `deepseek/deepseek-flash`, thinking `high` and `low`, tasks
`bugfix`/`feature`/`refactor` — the same cells the 2026-09-16 control used.

| Profile | Trials | Valid | Acceptance | Requests | Uncached input | Output | Total tokens | Reported cost | Wall s (sum / median) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| absent | 6 | 6/6 | 6/6 PASS | 52 | 89,179 | 20,537 | 1,203,604 | $0.057961 | 144.4 / 21.4 |
| present | 6 | 6/6 | 6/6 PASS | 52 | 89,904 | 22,589 | 1,203,693 | $0.060626 | 147.4 / 24.5 |
| delta | — | — | — | +0 | +725 (+0.8%) | +2,052 (+10.0%) | +89 (0.0%) | +$0.002665 (+4.6%) | +3.0 s (+2.1%) |

Per cell (absent → present); acceptance is PASS in every cell on both sides:

| Cell | Wall s | Requests | Uncached in | Total tokens | Cost |
| --- | --- | --- | --- | --- | --- |
| high bugfix | 21.6 → 16.1 | 8 → 7 | 14,957 → 13,529 | 182,191 → 151,974 | $0.009084 → $0.007427 |
| high feature | 29.2 → 30.0 | 10 → 8 | 16,608 → 14,217 | 245,314 → 191,900 | $0.011362 → $0.011620 |
| high refactor | 39.0 → 32.2 | 12 → 12 | 15,757 → 15,841 | 294,895 → 290,680 | $0.013549 → $0.012389 |
| low bugfix | 14.5 → 21.2 | 7 → 8 | 13,552 → 16,759 | 148,076 → 175,232 | $0.006855 → $0.009352 |
| low feature | 18.9 → 20.0 | 7 → 8 | 13,688 → 14,528 | 153,883 → 178,543 | $0.008046 → $0.008608 |
| low refactor | 21.2 → 27.8 | 8 → 9 | 14,617 → 15,030 | 179,245 → 215,364 | $0.009065 → $0.011230 |

Read it honestly: the aggregate total-token difference is +89 out of 1.2 M
(0.007%), and the per-cell movement is dominated by how many turns the model
chose to take. The `+10%` output and `+4.6%` cost columns are that turn-count
variance, not a skill effect, and the direction is not consistent across cells
(five cells up, one down on tokens). The only attributable figure is the +171
context tokens per request above.

## Method

- Manipulation: `mv ~/.pi/agent/skills/typesafe-ai` out for the absent batch and
  back for the present batch. Everything else is untouched.
- Control check that the manipulation worked, independent of the trials: a
  non-interactive Pi run asked to list its skills returned the same list in both
  states except `typesafe-ai`, which appears 4× in the present transcript and 0×
  in the absent one.
- Profile identity across all four checkpoints: `settings.json` sha256
  `92b26d57…cab305` and `models.json` sha256 `57b3cb37…163dc4` unchanged; the
  measured skill is `SKILL.md` sha256 `71ea90d7…b9389f52`.
- Pi 0.85.1, baseline `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1`, 300-second
  budget per trial, one run per cell, sequential.
- Batches ran absent first, then present.

## Verification

`verification.log` (private evidence) records, for all 12 published records:

- Every counter (requests, input, output, cache-read, total, cost) recomputed from
  the raw harness streams — exact for all 12, cost compared after the recorded
  1e-6 rounding, reported model identity `deepseek/deepseek-flash` throughout.
- The frozen acceptance and participant suites re-run from each recorded candidate
  in a fresh baseline clone: 24/24 runs agree with the published result. No
  failures, no deadline overruns, no provider errors, scope-clean in all 12 trials.
- Prompt identity: per cell the rendered prompt hash is identical between the two
  batches *and* equal to the 2026-09-16 control record for that cell, so the two
  batches really ran the same task text.

## Limits

- One run per cell: exploratory, no distribution and no significance claim.
- Batch order was fixed (absent, then present), so a warm-cache or time-of-day
  effect is not excluded from the wall-time and cost columns.
- These three tasks are plain Python edits with no semantic judgment to make, so
  the skill has nothing to do here. This measures what installing it costs, not
  whether TypeSafe's judgments are useful; that needs a task that actually calls
  the API.
- Pi arm and `deepseek/deepseek-flash` only; the GPT-6 and `union-alpha` cells were
  not re-run.
- Reported cost is the harness's own estimate, not verified billing.

## Evidence

- Private: `~/.megai/evidence/typesafe-bench/` — `run.sh` (driver),
  `profile-state.txt`, per-variant `trials/*/harness.jsonl` and `candidate.diff`,
  `overhead.json` per variant, `publish.py`, `verify.py`, `verification.log`,
  `aggregates.log`.
- Published: this file and [typesafe-skill.trials.json](typesafe-skill.trials.json)
  (12 sanitized records, each tagged `"profile": "typesafe-absent"` or
  `"typesafe-present"`; aggregates above recomputed from that file).
- Baseline checkout: `~/.megai/worktrees/megai-095a664e` (detached at the frozen SHA).
