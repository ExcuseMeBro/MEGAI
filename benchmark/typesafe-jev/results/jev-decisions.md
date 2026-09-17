# Jev vs deepseek-flash and MiniMax-M3 on a labelled triage set

Does a TypeSafe decision call replace a model prompt for the triage step? 24 short,
realistic repository requests, one run each, three arms:

| Arm | Interface |
| --- | --- |
| `jev` (TypeSafe System One, `jev-1.13.0`) | one `POST /v1/systemone` per item: typed `choice` + `score` + `noul` questions |
| `pi:deepseek/deepseek-flash` | non-interactive Pi run, strict-JSON answer prompt, thinking medium |
| `pi:minimax/MiniMax-M3` | same prompt, same settings |

Every arm receives the same label policy and the same request text; only the
interface differs. Labels are author-assigned against this repository's own
classification table, not an external gold set.

**No significance claim.** 24 items and one run per item is a smoke test: a
two-item gap is inside noise, and the effort labels are the softest part of the
fixture.

## Headline

| Arm | Type exact | Effort exact | Effort ±1 | Approval | Whole answer | Parse/OOV fails | p50 s | p95 s | Total cost | Cost / fully-correct answer |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `jev` | 22/24 | 11/24 | 22/24 | 24/24 | 9/24 | 0 | **0.8** | **0.9** | **$0.000723** | **$0.00008** |
| `pi:deepseek/deepseek-flash` | 23/24 | 13/24 | 23/24 | 24/24 | 13/24 | 0 | 3.1 | 5.2 | $0.012577 | $0.00097 |
| `pi:minimax/MiniMax-M3` | 23/24 | 11/24 | 23/24 | 24/24 | 11/24 | 0 | 4.1 | 23.9 | $0.101844 | $0.00926 |

- **Decision quality is tied.** Type accuracy differs by one item; the effort ±1
  column is 22–23/24 for all three; every arm got all five approval items right and
  all 19 non-approval items right, with no parse or out-of-vocabulary answers
  anywhere. Nothing here separates the arms on correctness.
- **Jev is 17× cheaper than deepseek-flash and 141× cheaper than MiniMax-M3** on
  the same 24 items, and 4×/5× faster at the median. Its cost per fully-correct
  answer is $0.00008 against $0.00097 and $0.00926.
- **The tail is the difference.** Jev's p95 is 0.9 s; deepseek's 5.2 s; MiniMax-M3's
  23.9 s — one item took over 20 s.
- Effort placement is where every arm falls short of an exact match: signed errors
  are within ±1 on 22–23 of 24 items, with a slight tendency to under-place
  (`-1` on 6–8 items per arm, `+1` on 4).

## Where the arms differ, per item

`want` is the author label (type/effort/approval); `p` is Jev's `noul` probability
for "needs approval" on that item. `ok` marks a fully correct answer.

| Item | want | jev | deepseek-flash | MiniMax-M3 |
| --- | --- | --- | --- | --- |
| t01 | bug/0/F | ok bug/0/F | ok bug/0/F | ok bug/0/F |
| t02 | bug/1/F | ok bug/1/F | ok bug/1/F | ok bug/1/F |
| t03 | bug/1/F | ok bug/1/F | ok bug/1/F | ok bug/1/F |
| t04 | bug/0/F | ok bug/0/F | ok bug/0/F | ok bug/0/F |
| t05 | feature/0/F | XX feature/1/F | XX feature/1/F | XX feature/1/F |
| t06 | feature/1/F | XX chore/1/F | XX chore/0/F | ok feature/1/F |
| t07 | feature/1/F | XX feature/0/F | XX feature/0/F | XX docs/0/F |
| t08 | refactor/1/F | ok refactor/1/F | ok refactor/1/F | XX refactor/2/F |
| t09 | refactor/2/F | XX refactor/1/F | XX refactor/1/F | XX refactor/1/F |
| t10 | refactor/1/F | XX chore/1/F | ok refactor/1/F | ok refactor/1/F |
| t11 | refactor/3/F | XX refactor/1/F | XX refactor/1/F | XX refactor/2/F |
| t12 | docs/0/F | ok docs/0/F | ok docs/0/F | ok docs/0/F |
| t13 | docs/1/F | XX docs/0/F | XX docs/0/F | XX docs/0/F |
| t14 | test/1/F | XX test/0/F | ok test/1/F | XX test/0/F |
| t15 | test/2/F | XX test/1/F | ok test/2/F | XX test/1/F |
| t16 | chore/0/F | ok chore/0/F | XX chore/1/F | ok chore/0/F |
| t17 | chore/0/T | XX chore/2/T p=0.98 | XX chore/1/T | XX chore/1/T |
| t18 | chore/0/T | XX chore/1/T p=0.98 | ok chore/0/T | ok chore/0/T |
| t19 | chore/0/T | ok chore/0/T p=0.96 | ok chore/0/T | ok chore/0/T |
| t20 | chore/0/T | XX chore/1/T p=0.94 | XX chore/1/T | XX chore/1/T |
| t21 | chore/1/T | ok chore/1/T p=0.93 | XX chore/0/T | XX chore/0/T |
| t22 | research/2/F | XX research/1/F | ok research/2/F | XX research/0/F |
| t23 | research/1/F | XX research/2/F | ok research/1/F | ok research/1/F |
| t24 | research/2/F | XX research/1/F | XX research/1/F | XX research/1/F |

Type misses: Jev `t06`→chore and `t10`→chore; deepseek `t06`→chore; MiniMax-M3
`t07`→docs. **`t06` is a contested label**: "add a CI check that runs the acceptance
gate whenever `lib/` changes" was labelled `feature`, and both text arms called it
`chore` while Jev agreed with them — the label is plausibly wrong, which is exactly
the kind of margin a 24-item fixture cannot settle.

## Jev's uncertainty signals

These are descriptive counts, not a calibration claim.

- `noul` on the five approval items: 0.98, 0.98, 0.96, 0.94, 0.93. On the other 19
  items the maximum is 0.34. **No value falls between 0.4 and 0.6**, so a 0.5
  threshold separated the two groups with a wide margin on this set.
- `choice` confidence: 20 of 24 answers at ≥0.9, all 20 correct; the four answers
  below 0.9 contained both of Jev's type errors. Low confidence pointed at the
  mistakes, but four low-confidence answers is far too few to call that calibration.

## Cost and latency notes

- Jev is priced from its published rate, $42 per billion input tokens ($0.042/Mtok),
  output free; the two model arms use Pi's host-reported cost.
- The two Pi arms pay Pi's whole system prompt on every call — ~18.5k prompt tokens,
  mostly served from cache — while Jev receives only the policy and the request
  (718–724 tokens). That gap is inherent to comparing a decision endpoint with a
  tool-bearing chat harness, and it is a large part of the cost difference; a bare
  provider API call would narrow it.
- Token columns are not directly comparable across providers: Pi's `input` is
  uncached input with the cached remainder reported separately, while MiniMax-M3
  reports ~18k per call as plain input. `cost$` is the comparable figure.

## Limits

- One run per item, 24 items; no repeatability measurement and no significance claim.
- Labels are author-assigned from the repository's own type table; `t06` is
  demonstrably contestable, and effort levels are the weakest of the three fields.
- Wrong answers cannot be attributed to the model alone: the label policy text is
  itself an interpretation of `AGENTS.md` written for this fixture.
- MiniMax-M3 was run at Pi defaults with thinking `medium`, same as deepseek-flash;
  other thinking levels were not tested.
- Jev reports a probability-weighted `score`; the level used here is its rounded
  position, with the raw value kept in the records.

## Evidence

- Raw per-call records: `results/jev-decisions.trials.json` (72 records; each keeps
  the arm's answer, the parsed decision, the correctness flags, wall time, tokens,
  cost, reported model and Jev's confidence/probability fields).
- Fixture and policy: [../items.json](../items.json).
- Private evidence: `~/.megai/evidence/jev-bench/` — `run.log`, per-call JSON, and
  `verification.log`, which re-derives every answer and flag from the stored raw
  responses, recomputes the aggregates, and checks the cost arithmetic and reported
  model identity (VERDICT PASS, 0 problems over 72 records).
