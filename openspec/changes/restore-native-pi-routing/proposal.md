## Why

The opt-in Antigravity headless worker repeatedly fails on tool permissions and blocks otherwise safe worktrees. The operator explicitly wants Pi/Paseo-native DeepSeek execution with GPT coordination and a bounded GPT Luna high fallback on confirmed DeepSeek insufficient balance.

Plane: project `59005e36-ecd4-46ed-bb42-f779858b20ce`, work item `82718bf4-53a3-447c-860e-10ff62b7d093` (MEGAI-160); no historical source marker.

## What Changes

- Retire Agy-specific Pi extension, preset, installer asset and active role instructions; preserve the standalone user-owned Agy CLI and credentials.
- Install a GPT Sol high coordinator, DeepSeek Flash high native worker, GPT Astra high reviewer profile without changing an already-running parent's selection.
- On a confirmed provider-specific DeepSeek insufficient-balance error, continue once on GPT Luna **high** with the original task evidence. Do not switch on auth/permission errors, silently spend, retry a busy writer or cycle providers.
- Preserve unrelated user settings and privately back up scoped runtime configuration before changing it. Keep bounded offline tests, exact-SHA independent security review and delivery gates.

## Capabilities

### New Capabilities
- `native-pi-routing`: explicit native worker configuration, permission-safe Agy retirement, and one-way balance fallback with high thinking.

### Modified Capabilities

None (there are no main OpenSpec capabilities; the historical `event-driven-pi-harness` change remains intact).

## Impact

`pi-defaults/AGENTS.md`, `pi-skill/{ADAPTIVE.md,delegation.md,role-routing/,model-fallback/,presets/}`, `lib/pi_model_policy.py`, focused installer/routing/fallback tests, owned files under `~/.pi/agent`. No other repositories, main/push, global Agy uninstall or authentication changes.
