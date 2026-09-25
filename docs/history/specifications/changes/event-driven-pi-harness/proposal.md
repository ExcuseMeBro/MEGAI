## Why

MEGAI-154 (`59005e36-ecd4-46ed-bb42-f779858b20ce` / `39f75567-dc61-49f0-b3f0-c7822436602a`) has an Antigravity-first local Pi profile that is not yet reproducible from the repository. Paseo already delivers real child-completion notifications, but the fallback instructions still encourage bounded wait timeouts.

## What Changes

- Persist an opt-in Antigravity/GPT Pi preset and its disabled DeepSeek runtime fallback without replacing the existing explicit economy preset or unrelated operator settings.
- Make the repo-owned Pi instructions event-first for Paseo Pi children: subscribe on creation and every background dispatch, yield to completion/error/permission events, and avoid artificial child-wait timeouts and polling. Preserve provider stall protection.
- Synchronize the Antigravity-first source policy, delegation guidance and tool metadata with the reviewed local profile; verify installer behavior and safety with focused tests.

## Capabilities

### New Capabilities

- `paseo-pi-harness`: Event-driven Pi child handoff and opt-in Antigravity/GPT local Pi profile.

### Modified Capabilities

None (there are no existing main specs).

## Impact

`pi-defaults/AGENTS.md`, `pi-skill/{ADAPTIVE.md,delegation.md,antigravity/index.ts,presets/}`, `lib/pi_model_policy.py`, focused tests and installed `~/.pi/agent` policy/configuration. No new daemon, Paseo transport modification, native Antigravity provider, credentials, primary checkout source writes, automatic main promotion or push. There is no historical source marker.
