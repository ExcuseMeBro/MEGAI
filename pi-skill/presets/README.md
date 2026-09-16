# Optional economy Pi preset

Use after explicitly choosing DeepSeek execution with GPT review. The
authoritative model and thinking values are in [economy.json](economy.json):
planner, scout, worker and reviewer. This is a user-selected default, not a model
allowlist or a guarantee that economy routing wins on other tasks. The three-task
pilot found scope and reporting errors even when functional tests passed.

`deepseek/deepseek-flash` (V4.1-Flash) covers planner at high thinking and scout and
worker at low; the reviewer stays on GPT. A three-task rerun of the frozen acceptance
suites held 3/3 at both levels while low cut wall time and reported cost against high
(see [`benchmark/pi-vs-omp/results/thinking-levels.md`](../../benchmark/pi-vs-omp/results/thinking-levels.md)).
Roles that share a model may differ in thinking: `megai-roles.json` keeps the per-role
level, and `settings.json` keeps the planner's level as the unambiguous native startup
default. Existing GPT role selections are retained. To upgrade an owned
older preset, explicitly reapply the same preset; ordinary wiring preserves it.
Historical model-specific settings remain user-owned and are not active role
routing. No credentials or provider registrations are removed.

The retired `mixed` preset differed only in its GPT planner. It is no longer
accepted: `--preset mixed` fails before any write. Reapply `economy` to replace an
owned `mixed` role file, or keep selecting a GPT planner per task instead.

From the reviewed `pi` checkout, preview then apply:

```sh
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --preset economy --check
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --preset economy
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
primary models may use the documented
[DeepSeek-first subagent fallback](../delegation.md#deepseek-first-subagent-fallback)
when permitted. Native-thinking mismatch or unavailable verification evidence stays
BLOCKED, not silent fallback. Apply [verified launch](../delegation.md#verified-launch) before context;
Paseo may report `xhigh` while the native Pi session actually uses `high`.

## Subagent-only fallback, parent unchanged

The delegation policy keeps configured DeepSeek planner/scout/worker roles primary
and uses `openai-codex/gpt-5.6-luna` (at the role's configured thinking level) for a permitted model-failure fallback or
confirmed DeepSeek `402: Insufficient Balance`. For that billing error, the parent
continues unfinished child work on that fallback without retrying DeepSeek or waiting
for a top-up; see the
[exact trigger and boundaries](../delegation.md#confirmed-deepseek-balance-exhaustion).
Reviewer routing is unchanged. This is a parent-consumed instruction, not an automatic Pi failover
engine or a new `settings.json` key. Refresh the owned delegation policy without
`--preset` when only this child fallback is wanted; primary role data and all native
model settings stay untouched. Do not select a preset just to add a fallback.

After a policy-only refresh, reload/reopen Pi; no startup defaults change.
After explicitly applying a full preset, restart Pi to use its new startup defaults.
An already-running parent's model is not changed by editing settings. Per-model
startup levels do not override an explicitly selected Paseo thinking value.
`--remove` retires owned policy/role files but keeps the user's native model
preferences; restore a private backup explicitly if those preferences should be
rolled back. Do not combine `--remove` with `--preset`.
