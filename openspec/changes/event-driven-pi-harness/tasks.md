## 1. Event-driven handoff

- [x] 1.1 Add focused policy regression assertions in `tests/pi_event_harness.py` and observe failure against the old bounded-wait wording.
- [x] 1.2 Update repo-owned Paseo Pi delegation and AGENTS policy to require matching `notifyOnFinish` events/yield without child-wait timeouts or polling, while retaining provider stall limits; verify `python3 -B -m unittest discover -s tests -p pi_event_harness.py` passes.

## 2. Reproducible Antigravity profile

- [x] 2.1 Add an opt-in GPT-native Antigravity preset and transactional installer handling for empty fallback map; extend `tests/pi-role-routing.mjs` to cover preservation/economy/opt-in and verify it passes.
- [x] 2.2 Sync repo-owned Agy-first Pi policy, adaptive skill, delegation guide and Agy tool prompt metadata with reviewed local behavior; verify `tests/pi-antigravity.mjs`, `tests/pi-role-routing.mjs`, and `tests/pi_defaults.py` pass.

## 3. Validation and handoff

- [x] 3.1 Validate the OpenSpec delta with `openspec validate event-driven-pi-harness --strict --no-interactive`, inspect the full diff and commit only task-owned files.
- [x] 3.2 Apply source-owned local Pi assets with a private backup and verify installed/source parity and a real event notification or existing recorded Paseo event. Guarded evidence and independent review are delivery gates, not implementation tasks.
