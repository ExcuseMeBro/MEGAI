## Why

The guarded acceptance checker hardcodes the independent reviewer's harness (`pi`) and thinking level (`high`) in `lib/acceptance_gate.py`. That conflicts with the current user-approved reviewer configuration (Luna at `medium`), so a legitimate review cannot be recorded without falsifying its metadata. Fix the conflict by letting a schema-2 contract freeze the exact reviewer policy it was reviewed under, while legacy contracts keep today's Pi/high requirement.

Plane project/work item: `59005e36-ecd4-46ed-bb42-f779858b20ce` / `eeb46cbe-899e-4f1f-a5ff-559754d8fee5`.

## What Changes

- Schema-2 contracts MAY carry an optional top-level `reviewer` object: `harness`, `model` (provider/model) and `thinking`. Its presence freezes the exact independent reviewer policy for that task.
- `collect` copies the frozen policy into the generated review template (`harness`, `model`, `thinking`) instead of the hardcoded Pi/high defaults.
- `check` validates review evidence exactly against a frozen policy: the stored harness, provider/model and thinking must match byte-for-byte. A `medium` (or `low`) review passes only when the contract explicitly froze that thinking level.
- A frozen-policy mismatch, and a policy that omits any of the three fields, remain BLOCKED. Schema-1 contracts and schema-2 contracts without `reviewer` retain the existing required `harness: pi`, `thinking: high` behavior and the provider/model syntax check.
- Regression tests extend `tests/acceptance_gate.py` for explicit Luna/medium PASS, mismatch rejection and legacy Pi/high behavior; `pi-skill/acceptance/reference.md` and `contract.example.json` document the optional field.

## Capabilities

### New Capabilities

- `acceptance-reviewer-policy`: Contract-frozen independent reviewer policy for the local acceptance gate, including evidence validation, collection defaults and legacy compatibility.

### Modified Capabilities

None; this repository has no existing main capability specs.

## Impact

Affected code paths: `lib/acceptance_gate.py` (`_contract`, `check` review validation, `collect` review template), regression tests in `tests/acceptance_gate.py`, and documentation in `pi-skill/acceptance/reference.md` plus `pi-skill/acceptance/contract.example.json`. No change to evidence schema, receipt format, Plane integration, model routing, installers, or other harnesses. Non-goals: changing the default legacy requirement, adding a reviewer-model allowlist, allowing arbitrary/unfrozen `medium` reviews, main promotion or push. Rollback is reverting the single commit; contracts without `reviewer` behave exactly as before.
