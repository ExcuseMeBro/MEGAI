# Optional mixed Pi preset

Use after explicitly choosing mixed GPT/MiniMax routing. The authoritative model
and thinking values are in [mixed.json](mixed.json): planner, scout, worker and
reviewer. This is a user-selected default, not a model allowlist or a guarantee
that mixed routing wins on other tasks. The three-task pilot found scope and
reporting errors even when functional tests passed.

From the reviewed `pi` checkout, preview then apply:

```sh
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --preset mixed --check
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --preset mixed
```

The explicit flag writes `megai-roles.json` in the Pi agent directory and updates
native `settings.json`: startup provider/model/thinking from the planner, plus
`modelThinkingLevels` for each selected model. Other model entries, resources,
permissions, transport, credentials and provider catalogs remain untouched.
Ordinary policy installation does not select a preset or change model settings.
Custom/conflicting role files and malformed/symlinked settings block the combined
write. The existing installer saves private pre-change backups and ownership
receipts; repeating the same preset is idempotent.

`megai-roles.json` is **MEGAI parent policy data**, not a native Pi setting, Paseo
profile, automatic dispatcher or sandbox. The parent reads it only when selecting
a needed role, then passes the explicit `pi/PROVIDER/MODEL` and thinking to Paseo.
Direct tools remain preferable for a bounded task; no mandatory scout/planner/worker/
reviewer fanout. Explicit user/task model choices override the preset. Missing
models, native-thinking mismatch or unavailable evidence are BLOCKED, not silent
fallback. Apply [verified launch](../delegation.md#verified-launch) before context;
Paseo may report `xhigh` while the native Pi session actually uses `high`.

Restart Pi or open a fresh session to load the new startup defaults and policy.
An already-running parent's model is not changed by editing settings. Per-model
startup levels do not override an explicitly selected Paseo thinking value.
`--remove` retires owned policy/role files but keeps the user's native model
preferences; restore a private backup explicitly if those preferences should be
rolled back. Do not combine `--remove` with `--preset`.
