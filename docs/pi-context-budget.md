# Native Pi context budget

Optional client-side budget for the two GPT models in
[`context-budget.models.json`](../pi-skill/context-budget.models.json).
It uses Pi's documented per-model `modelOverrides.contextWindow`; no extension,
router or custom compactor. It does not change the provider's physical capacity.

With native compaction enabled, reserve=16384 and keepRecent=20000:

- GPT's original 272000 budget waits until usage exceeds 255616 tokens.
- The 65536 budget triggers native compaction above 49152 tokens.
- Native summaries and retained recent messages replace older context sent to the
  model; original session history remains on disk. No transcript is deleted.

Model identity, provider/auth, thinking, output limits and pricing stay unchanged.
Other models, including the runtime-resolved DeepSeek alias, are untouched.
Explicit compaction opt-out and project overrides still apply. This is an earlier
native trigger, not a hard per-request token cap or a guarantee about accuracy,
latency or billing. Summarization itself costs tokens and can omit details; use
original files/receipts when exact evidence is needed. The installed Jev fast
compaction ([`docs/pi-jev-compaction.md`](pi-jev-compaction.md)) changes what a
compaction costs and keeps: it keeps text, calls and wanted results verbatim and
still falls back to Pi's own summary for focused, overflow or keyless runs.

## Apply and activate

`lib/pi_context_budget.py` is the explicit, opt-in installer. It merges only the
`contextWindow` fields named in the shipped template, preserves every other key,
provider, credential and setting, and refuses a user-owned value instead of
overwriting it. Writes go through the shared ownership receipts with a private
backup; `--check` is the default and never writes.

```bash
megai budget --check          # preflight, no writes
megai budget --apply
megai budget --verify          # real native model loader
megai budget --apply --window 131072
megai budget --remove          # owned fields only
```

From a checkout, run `python3 lib/pi_context_budget.py` with the same flags.

`--window` replaces the template value for every target and is bounded to
32768..2000000. `--verify` loads the installed `models.json` with Pi's own model
loader offline and fails when the file does not actually change the native budget,
so a written-but-ineffective file is not reported as active. It needs Node and the
Pi package (`PI_PACKAGE_ROOT`, or a resolvable `pi` executable); when neither is
available it stops as blocked rather than claiming success.

In interactive Pi, reopen `/model` and reselect the same model, or start a new Pi
session. A fresh native loader sees the change; an already-running agent must not
be assumed to have reloaded. In an oversized existing session, `/compact` requests
native summarization; it does not delete the original transcript.

## The trade-off is measured, not assumed

A smaller window cuts the per-turn prompt, but each compaction is itself a
full-context summarization request and can omit detail. In the observed
2026-09-15 window (see [pi-usage-report.md](pi-usage-report.md)) the GPT parent ran
at 91,662 prompt tokens per turn and reached a 255,852-token prompt before the
native trigger, while only 4 compactions and reported $4.42 of summarization work
occurred in 14 days. A substantially smaller window therefore removes a large
per-turn term and adds summarization work at the same time; the net effect is not
knowable without measuring. Compare equal tasks in fresh sessions with

```bash
megai report --text
```

before and after. Nothing in this repository claims the cap saves tokens.

## Verification

```sh
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-context-budget.mjs
# Read the actual installed preference without a model/provider request:
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-context-budget.mjs "$HOME/.pi/agent/models.json"
# Installer behaviour, ownership and native verification:
PYTHONDONTWRITEBYTECODE=1 python3 tests/pi_context_budget.py
```

The offline test uses the real native model loader and compaction predicate. It
checks the 140k regression, exact threshold, opt-out, recent-retention default and
unchanged model metadata. It does not generate a summary or measure end-to-end
speed; compare equal tasks in fresh sessions for that.
