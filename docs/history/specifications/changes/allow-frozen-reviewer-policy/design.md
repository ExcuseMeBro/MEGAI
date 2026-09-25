## Context

`lib/acceptance_gate.py` owns the guarded acceptance CLI (`snapshot`, `run`, `collect`, `check`). `_contract` (line 343) parses and strictly whitelists contract fields. For schema 2 it adds `task_type`; it has no place for a reviewer policy. The `check` review validator (lines ~596-612) requires the literal values `review["harness"] == "pi"` and `review["thinking"] == "high"`; `collect` (line 768) hardcodes the same `"harness": "pi"` and `"thinking": "high"` in the draft review template.

The task's own acceptance criteria (Plane `eeb46cbe-899e-4f1f-a5ff-559754d8fee5`) are explicit: schema-2 contracts may freeze an exact reviewer policy; `collect` emits it; `check` validates exactly against it; `medium` passes only when frozen; mismatches stay BLOCKED; legacy contracts keep Pi/high; tests cover medium PASS, mismatch rejection and legacy high.

## Goals / Non-Goals

**Goals:**
- Allow an optional, explicit frozen reviewer policy in schema-2 contracts.
- Validate review evidence against that policy exactly; keep fail-closed behavior for mismatches.
- Preserve 100% of existing schema-1 and no-`reviewer` schema-2 behavior.
- Add focused regression tests and reference documentation.

**Non-Goals:**
- Adding a reviewer model allowlist or validating model semantics beyond the existing `provider/model` syntax.
- Changing the evidence schema, receipts, snapshot logic, Plane integration, installers or other harnesses.
- Accepting unfrozen `medium`/`low` reviews or bypassing the independent-review gate.

## Decisions

### One optional top-level `reviewer` object, not per-criterion or a new schema

Contract field shape: `"reviewer": {"harness": "pi", "model": "openai-codex/gpt-5.6-luna", "thinking": "medium"}`. This mirrors the existing review evidence keys, so `check` and `collect` compare/copy three fields directly. `_contract` allows the key only for schema 2 (`keys.add("reviewer")`), keeps it optional, and requires all three fields exactly when present. Per-criterion policies were rejected: one independent reviewer covers the whole task. A new schema version was rejected: schema 2 is the current contract and the field is optional and backward-compatible.

`thinking` accepts `low`, `medium` or `high` (the configured role levels); `harness` is a nonempty trimmed string; `model` reuses the existing `provider/model` syntax rule already applied to review evidence.

### Defaults stay Pi/high; exact match only when frozen

`check` derives the expected harness/thinking from `contract.get("reviewer")`: frozen values are compared exactly, otherwise the existing required `pi`/`high` remain. The model rule is unchanged when nothing is frozen (syntax only) and becomes an exact string equality when frozen. This means an unfrozen `medium` review is still BLOCKED, satisfying "medium passes only when explicitly frozen".

### Collection copies, never verifies

`collect` only fills the draft review template (`harness`, `model`, `thinking`) from the frozen policy and leaves `session_id`, observations and `verdict` incomplete as today. It never marks a task accepted; the existing `BLOCKED` draft semantics are preserved.

## Compatibility, Privacy and Rollback

- Schema 1 rejects `reviewer` exactly as it rejects any unknown key, so old contracts cannot silently gain a policy.
- Schema-2 contracts without `reviewer` behave byte-for-byte as before (Pi/high, provider model syntax check).
- No new I/O surfaces: the policy lives in the already-external contract JSON; no secrets, credentials or personal data are read or logged.
- Rollback is reverting the change commit; existing contracts are unaffected because the field is optional.

## Risks / Trade-offs

- **Self-referential gate change**: the same CLI validates the change's own acceptance. Mitigation: freeze RED evidence with the unmodified CLI, then rerun the identical command after the fix; keep the legacy path covered so unrelated tasks are unaffected.
- **Weakened-review risk**: a contract author could freeze a weak reviewer. Mitigation: freezing is explicit, reviewed contract content; the gate still requires an independent session and complete criterion evidence.

## Verification

- Focused `tests/acceptance_gate.py` CLI tests: frozen Luna/medium PASS, mismatch BLOCKED, legacy Pi/high PASS plus unfrozen medium BLOCKED, `collect` template emission.
- `openspec validate allow-frozen-reviewer-policy --strict`.
- Ruff on changed Python; independent review of the diff and RED/GREEN causality.
