# Optional Pi presets

`--preset antigravity` is the opt-in local Pi profile: fresh sessions start on
`openai-codex/gpt-6-sol` at high thinking, all native roles are GPT (reviewer
`gpt-6-astra`), and `model-fallback.json` has an empty map so a GPT provider
failure never silently moves to DeepSeek. Agy is a sandboxed tool for eligible
clean linked Git worktrees, **not** a native Pi/Paseo provider. Existing auth,
other settings and model catalog entries remain operator-owned. Before opting in,
back up the local Pi configuration privately and verify that its AGENTS base is the
current reviewed `pi-defaults/AGENTS.md`. An older MEGAI default profile must first
refresh that base while preserving injected `<!-- megai:* -->` blocks; never overwrite
custom/unowned instructions. The complete owned-policy refresh also needs the
adaptive skill and delegation guide, so preview/apply from the reviewed task checkout:

```sh
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --adaptive --preset antigravity --check
MEGAI_SOURCE="$PWD" python3 -B lib/pi_model_policy.py --adaptive --preset antigravity
```

The preset fails before writing if the AGENTS base remains stale or the adaptive
skill/delegation guide cannot be safely refreshed; `--adaptive` updates only owned
assets, not the AGENTS base.
For a verified copy of the exact pre-Agy MEGAI default profile in
`tests/fixtures/pi-agents-pre-antigravity.md`, the scoped upgrade below backs up
`~/.pi/agent/AGENTS.md` privately and preserves injected blocks. It refuses any
custom/unrecognized base; run from this reviewed checkout **before** the preset:

```sh
python3 -B - <<'PY'
from pathlib import Path
import runpy, shutil, tempfile

path = Path.home() / '.pi/agent/AGENTS.md'
if path.is_symlink() or not path.is_file():
    raise SystemExit('Refusing missing or symlinked AGENTS.md')
old = path.read_bytes()
profile = runpy.run_path('pi-defaults/install.py')
legacy = Path('tests/fixtures/pi-agents-pre-antigravity.md').read_bytes().strip()
if profile['INJECTED_BLOCK'].sub(b'', old).strip() != legacy:
    raise SystemExit('Custom AGENTS base: reconcile manually; no changes made')
source = Path('pi-defaults/AGENTS.md').read_bytes()
backup = Path(tempfile.mkdtemp(prefix='pi-agents-backup-', dir=Path.home() / '.pi'))
shutil.copy2(path, backup / 'AGENTS.md')
path.write_bytes(profile['profile_agents_md'](old, source))
print('Private backup:', backup)
PY
```

Stop for manual reconciliation if the base differs; do not use the full default
installer or `--reset` to bypass an ownership refusal. The test seeds that
historical profile, verifies safe refusal, then upgrades the base with `--adaptive`.
The fallback file changes only on explicit Antigravity opt-in; an unowned,
conflicting file is refused, not overwritten. A normal policy refresh leaves
that file and native model settings alone. The preset-free role file is valid
schema-1 Pi guidance and does not enable `economy` routing. Reopen Pi for startup
defaults; an active session retains its selected model.

`--preset economy` remains available after explicitly choosing DeepSeek execution
with GPT review. Its authoritative model and thinking values are in
[economy.json](economy.json):
planner, scout, worker and reviewer. This is a user-selected default, not a model
allowlist or a guarantee that economy routing wins on other tasks. The three-task
pilot found scope and reporting errors even when functional tests passed.

`deepseek/deepseek-flash` (V4.1-Flash) covers planner at high thinking and scout and
worker at low; the reviewer stays on GPT. A three-task rerun of the frozen acceptance
suites held 3/3 at both levels while low cut wall time and reported cost against high
(see [`benchmark/pi-vs-omp/results/thinking-levels.md`](../../benchmark/pi-vs-omp/results/thinking-levels.md)).
Roles that share a model may differ in thinking: `megai-roles.json` keeps the per-role
level, and `settings.json` keeps the planner's level as the unambiguous native startup
default. Write levels the model actually accepts: the installer validates the level name,
not model support, and `deepseek-flash` maps `minimal` and `medium` to no thinking
parameter at all, so `low`, `high` and `max` are its real levels. Existing GPT role
selections are retained. To upgrade an owned
older preset, explicitly reapply the same preset; ordinary wiring preserves it.
Historical model-specific settings remain user-owned and are not active role
routing. No credentials or provider registrations are removed.

`economy` and `antigravity` are the only presets: `--preset mixed` is rejected
before any write, and a role file that still names `mixed` is ignored. Reapply
`economy` to replace an owned `mixed` role file, or keep selecting a GPT planner
per task instead.

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
reviewer fanout. Explicit user/task model choices override the preset. The existing
economy role-context extension retains its DeepSeek-specific fallback guidance when
those roles are explicitly selected. The Antigravity preset has no DeepSeek fallback.
Native-thinking mismatch or unavailable verification evidence stays BLOCKED, not
silent fallback. Apply [verified launch](../delegation.md#verified-launch) before context;
Paseo may report `xhigh` while the native Pi session actually uses `high`.

## Native models and event handoff

Model preferences and verified launches remain explicit; selecting either preset
is not an automatic agent dispatch. Paseo Pi children use `notifyOnFinish: true`
on creation and each background send, with no child-wait deadline or polling.
Provider request/stall safeguards and Agy's bounded CLI calls remain separate.
Refresh policy without `--preset` when no model/default change is wanted.

After a policy-only refresh, reload/reopen Pi; no startup defaults change.
After explicitly applying a full preset, restart Pi to use its new startup defaults.
An already-running parent's model is not changed by editing settings. Per-model
startup levels do not override an explicitly selected Paseo thinking value.
`--remove` retires owned policy/role files but keeps the user's native model
preferences; restore a private backup explicitly if those preferences should be
rolled back. Do not combine `--remove` with `--preset`.
