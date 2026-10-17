# Optional Pi presets

The `native` preset selects GPT Sol high as the startup default and per-model
thinking preferences. It no longer installs role routing. It installs the single
fallback edge from `deepseek/deepseek-flash` to `openai-codex/gpt-6-luna`:
only a confirmed DeepSeek 402 insufficient-balance error continues once on Luna at
high thinking. Auth/permission errors, shared outages, other failures and uncertain
writes do not trigger model hopping.

The independent `economy` preset selects DeepSeek Flash high as the startup
default. Legacy role labels in preset JSON are only used to derive startup/per-model
preferences; no role configuration is installed or consumed by the harness.
The active parent model/thinking and unrelated settings remain unchanged until a
fresh session uses explicit defaults.

Preview and apply a selected profile from the reviewed checkout:

```sh
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --adaptive --preset native --check
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --adaptive --preset native
# Or independently select economy:
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --preset economy --check
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --preset economy
```

The native preset requires `--adaptive`: it verifies the installed adaptive and
delegation skills and safely migrates only the exact previous managed AGENTS base,
preserving injected blocks; unknown/custom base edits are refused. The installer
privately backs up owned settings changes and preserves unrelated
settings, credentials, provider catalogs and resource filters. It retires only
receipt-owned managed assets; an unowned resource at a retired path blocks installation
for manual reconciliation. Ordinary policy refresh does not select a preset or change
native model settings. An already-running parent's model is never switched by editing
settings; open a fresh Pi session to use updated startup defaults.

Policy refresh retires receipt-owned `megai-roles.json` and the role-routing
extension. Explicit user/task model choices govern delegation. The
native profile's model-fallback extension preserves the failed task context and queues
a follow-up only while the Pi run is active. A failed Luna continuation cannot cycle
back to DeepSeek.
