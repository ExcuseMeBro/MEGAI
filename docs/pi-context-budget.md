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
original files/receipts when exact evidence is needed.

## Apply and activate

Back up `~/.pi/agent/models.json` privately. If absent, the template can supply it;
otherwise merge only the two `contextWindow` fields, preserving existing entries.
This is a separate native preference: the token-profile installer does not apply
or remove it automatically. Restore the prior fields to undo it.

In interactive Pi, reopen `/model` and reselect the same model, or start a new Pi
session. A fresh native loader sees the change; an already-running agent must not
be assumed to have reloaded. In an oversized existing session, `/compact` requests
native summarization; it does not delete the original transcript.

## Verification

```sh
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-context-budget.mjs
# Read the actual installed preference without a model/provider request:
PI_PACKAGE_ROOT=/path/to/pi-coding-agent node tests/pi-context-budget.mjs "$HOME/.pi/agent/models.json"
```

The offline test uses the real native model loader and compaction predicate. It
checks the 140k regression, exact threshold, opt-out, recent-retention default and
unchanged model metadata. It does not generate a summary or measure end-to-end
speed; compare equal tasks in fresh sessions for that.
