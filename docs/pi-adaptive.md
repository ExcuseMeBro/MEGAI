# Adaptive Pi: less ceremony, real verification

Pi now installs a short bootstrap and loads detailed delegation only when needed.
The installed `megai` skill routes clear reversible work to one parent, focused
checks and self-review. Security/data integrity, payments, migrations, shared-state
concurrency, consequential cross-module changes, safety/installer policy and
multi-repo delivery use the existing formal independent acceptance gate. Explicit
repo/user requirements still win. A failed gate cannot become a routine PASS.

Plane remains boundary-only tracking. Worktree isolation, private configuration
backups, cooperative integration reservations and separate main/push approval stay.
No agents, daemons, indexes or provider requests are added at startup. The acceptance
CLI itself is unchanged. This reduces required workflow steps for routine work; it
is not a measured end-to-end latency, quality or token-saving claim.

## MiniMax-first, explicitly selected

Ordinary wiring preserves native model/auth/role preferences. To deliberately
select the new economy preset after installing these sources:

```bash
python3 -B ~/.megai/lib/pi_model_policy.py --adaptive --preset economy --check
python3 -B ~/.megai/lib/pi_model_policy.py --adaptive --preset economy
```

This sets next-session defaults and planner/worker roles to `minimax/MiniMax-M3`
with high thinking, scout to `minimax/MiniMax-M2.7-highspeed` with medium thinking,
and guarded reviewer to `openai-codex/gpt-5.6-sol` with high thinking. Roles are
preferences, not mandatory agent launches. Routine MiniMax parent work does not
launch GPT; GPT is reserved for guarded review or a concrete model-specific
failure. Existing `mixed` selection remains available and unchanged.

`--adaptive` refreshes only Pi workflow resources; it does not perform unrelated
legacy-store migrations or claim full-distribution health. Source publication is a
separate normal MEGAI installation/update operation.

The command preflights ownership, privately backs up managed edits and preserves
credentials, unrelated settings and resource exclusions. A customized roles file
is preserved with an error rather than overwritten; reconcile it deliberately.
No silent live-session switch: open a fresh Pi session and verify the model. An
existing Paseo tab can retain its own explicit model; choose Pi / MiniMax-M3 / high
there. Running writers must finish before reload/restart.

## Verification

```bash
python3 -B tests/pi_adaptive_policy.py
python3 -B tests/pi_model_policy.py
python3 -B tests/pi_mixed_preset.py
```

Tests exercise real installer commands in disposable HOME directories: bounded
bootstrap, Pi-only adaptive routing, owned legacy migration, collision refusal,
idempotence, explicit economy selection and preservation of native resources.
Policy assertions prove shipped instructions, not model compliance on real tasks.
Measure actual task time, user interventions and defects before claiming speed.
