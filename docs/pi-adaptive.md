# Adaptive Pi: less ceremony, real verification

Pi now installs a short bootstrap and loads detailed delegation only when needed.
The installed `megai` skill defaults to three steps: **locate/edit → one necessary
check with inline self-review → deliver/stop**. Known routine changes do not need
an automatic scout, new test file, full suite or separate review/report stage.
Wording-only docs use a diff/link check or installed-file parity; behavior changes
use the smallest relevant test/reproduction and any necessary diagnostics.

Classify actual effects, not filenames or file count. Harmless skill/AGENTS.md prose
and installing already-reviewed policy bytes are not automatically guarded.
Security/data integrity, payments, migrations, shared-state concurrency,
consequential cross-module changes, behavior-changing safety/installer/acceptance
policy and multi-repo delivery retain formal source-current acceptance without a
mandatory separate reviewer. Instructions that alter approval, validation or
ownership checks remain guarded. Explicit repo/user requirements still win. A failed
gate cannot become a routine PASS. The parent self-reviews current raw evidence
without repeating passing suites by default; only a concrete unresolved risk
justifies extra checks. Explicit user-requested independent review remains available.

Plane remains boundary-only tracking. Worktree isolation, private configuration
backups, cooperative integration reservations and separate main/push approval stay.
No agents, daemons, indexes or provider requests are added at startup. New acceptance
contracts use review-free schema 3; historical contracts retain their original
validation. This reduces required workflow steps for routine work; it
is not a measured end-to-end latency, quality or token-saving claim.

## Explicit native and economy profiles

Ordinary wiring preserves native model/auth/role preferences. To select the native
profile for new sessions:

```bash
python3 -B ~/.megai/lib/pi_model_policy.py --adaptive --preset native --check
python3 -B ~/.megai/lib/pi_model_policy.py --adaptive --preset native
```

The native profile uses `openai-codex/gpt-6-sol` high for coordination, one
`deepseek/deepseek-flash` high implementation worker and `openai-codex/gpt-6-astra`
high reviewer only on explicit request. The separate `economy` preset remains
independently available: it
uses DeepSeek Flash high planning, low scout/worker, and GPT Sol high review. Roles are
parent guidance, not mandatory agent launches or a dispatcher. Explicit user/task
choices override either profile, and an already-running parent's model/thinking never
changes from installer writes.

Only a confirmed DeepSeek 402 insufficient-balance error allows one continuation on
`openai-codex/gpt-6-luna` at high thinking, preserving existing task context. Auth or
permission errors, shared outages, other errors and uncertain writes do not trigger
model hopping; failed Luna continuation cannot cycle back to DeepSeek.

A fresh child launch verifies the Paseo harness `pi` separately, then uses the
status-provided handle for the same current native session ID. Match the qualified
status model to native `model_change.provider` and `model_change.modelId`. Native
`thinking_level_change.thinkingLevel` must match effective status thinking. Prefer
these proven native records; the neutral runtime-check prompt remains the fallback
when those records are missing, stale, ambiguous, or come from a restored agent on a
different branch. Historical workflow metrics are at
[`docs/audits/pi-fast-workflow.md`](audits/pi-fast-workflow.md).

The installer preflights ownership, privately backs up managed edits and preserves
credentials, unrelated settings and resource exclusions. A customized roles file is
preserved with an error rather than overwritten; reconcile it deliberately. Ordinary
wiring keeps existing role/model preferences. Open a fresh Pi session to use updated
startup defaults; an existing Paseo tab retains its explicit selection.

## One decision call per boundary, speculative branches included

Measured 2026-09-19 (30 comparisons on the then-active hosted decision endpoint, 10
realistic MEGAI decision boundaries): bundling a follow-up for
*every* branch option into the same call as the branch question, and using only the
selected branch's answer, returned the identical answer 30/30 times, took 0.78s median
against 1.57s for two sequential calls, and cost 544 input tokens against 896, with no
`noul` probability moving more than 0.03. A second call stays required when the
follow-up depends on state the chosen branch itself produces — the only disagreement
(3/30, one item, low confidence in both arms).

## Verification

```bash
python3 -B tests/pi_adaptive_policy.py
python3 -B tests/pi_model_policy.py
python3 -B tests/pi_deepseek_preset.py
```

Tests exercise real installer commands in disposable HOME directories: bounded
bootstrap, Pi-only adaptive routing, owned legacy migration, collision refusal,
idempotence, explicit economy selection and preservation of native resources.
Policy assertions prove shipped instructions, not model compliance on real tasks.
Measure actual task time, user interventions and defects before claiming speed.
