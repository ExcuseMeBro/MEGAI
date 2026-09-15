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
policy and multi-repo delivery retain formal independent acceptance. Instructions
that alter approval, validation or ownership checks remain guarded. Explicit
repo/user requirements still win. A failed gate cannot become a routine PASS.
A guarded reviewer reads current raw evidence instead of repeating passing suites
by default; only a concrete unresolved risk justifies extra checks. Editorial
preferences do not create repair loops unless they violate the frozen contract
or cause a demonstrated safety/correctness failure.

Plane remains boundary-only tracking. Worktree isolation, private configuration
backups, cooperative integration reservations and separate main/push approval stay.
No agents, daemons, indexes or provider requests are added at startup. The acceptance
CLI itself is unchanged. This reduces required workflow steps for routine work; it
is not a measured end-to-end latency, quality or token-saving claim.

## DeepSeek-first, explicitly selected

Ordinary wiring preserves native model/auth/role preferences. To deliberately
select the new economy preset after installing these sources:

```bash
python3 -B ~/.megai/lib/pi_model_policy.py --adaptive --preset economy --check
python3 -B ~/.megai/lib/pi_model_policy.py --adaptive --preset economy
```

This sets next-session defaults and planner/scout/worker roles to
`deepseek/deepseek-flash` (V4.1-Flash) with high thinking, and guarded reviewer to
`openai-codex/gpt-5.6-sol` with high thinking. Shared model roles use one consistent
per-model startup level; scout also uses high. Roles are preferences, not mandatory
agent launches. Routine DeepSeek parent work does not launch GPT; GPT is reserved
for guarded review or a concrete model-specific failure. The retired `mixed` preset
differed only in a GPT planner; one `economy` preset now covers DeepSeek planning,
scout and worker with a GPT reviewer.

A healthy DeepSeek parent performs its own routine work directly. With an
inherited GPT/Paseo parent and the `economy` preset, substantial bounded
implementation goes to one DeepSeek worker instead of being duplicated in GPT;
trivial read-only or single-edit work may stay direct when launching a worker
would be disproportionate. The parent still owns scope, validation and
guarded review or integration. Explicit user/task model choices always
override this default; the parent's model is never silently switched and an
agent team or every role is never required.

A fresh child launch verifies the Paseo harness `pi` separately, then uses the
status-provided handle for the same current native session ID. Match the qualified
status model `deepseek/deepseek-flash` to native `model_change.provider=deepseek` and
`model_change.modelId=deepseek-flash`; do not compare harness `pi` with model provider
`deepseek`. Native `thinking_level_change.thinkingLevel` must match effective status
thinking. Prefer these proven native records; the neutral runtime-check prompt
remains the fallback when those records are missing,
stale, ambiguous, or come from a restored agent on a different branch. The
retrospective metrics for three real repository tasks, the neutral env-check
sample and historical writer startup verification live at
[`docs/audits/pi-fast-workflow.md`](audits/pi-fast-workflow.md); the frozen
redacted dataset is in
[`docs/audits/pi-task-sample.json`](audits/pi-task-sample.json).

`--adaptive` refreshes only Pi workflow resources; it does not perform unrelated
legacy-store migrations or claim full-distribution health. Source publication is a
separate normal MEGAI installation/update operation.

The command preflights ownership, privately backs up managed edits and preserves
credentials, unrelated settings and resource exclusions. A customized roles file
is preserved with an error rather than overwritten; reconcile it deliberately.
Explicitly reapply an owned older preset to update its roles. Ordinary wiring
keeps existing role/model preferences; historical per-model settings and provider
credentials are not deleted. Publishing this branch does not install it locally.
No silent live-session switch: open a fresh Pi session and verify the model. An
existing Paseo tab can retain its own explicit model; choose Pi / deepseek-flash / high
there. Running writers must finish before reload/restart.

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
