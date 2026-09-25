## 1. Regression tests (TDD RED)

- [x] 1.1 Extend `tests/acceptance_gate.py` with schema-2 fixtures and cover Frozen reviewer policy in schema-2 contracts: explicit `provider/model` + `medium` PASS, malformed/partial policy BLOCKED, and schema-1 rejection. Verify the new tests fail against the unmodified `lib/acceptance_gate.py` with an assertion failure, not an import/setup error, and capture the RED receipt.
- [x] 1.2 Add coverage for Exact evidence validation against the frozen policy and Collection emits the frozen reviewer policy: harness/model/thinking mismatch BLOCKED, legacy contract Pi/high PASS, legacy `medium` BLOCKED, and `collect` template emission. Verify each fails for the missing feature and passes after implementation.

## 2. Contract parsing and validation

- [x] 2.1 Implement Frozen reviewer policy in schema-2 contracts in `_contract`: allow the optional `reviewer` key only for schema 2, require exactly `harness`/`model`/`thinking`, validate harness nonempty, model syntax and thinking level, and reject it for schema 1. Verify focused parser tests and `openspec validate --strict`.
- [x] 2.2 Implement Exact evidence validation against the frozen policy in `check`: compare review harness/model/thinking exactly when frozen, keep `pi`/`high` when absent, and return BLOCKED with a clear reason on mismatch. Verify the RED tests turn green without weakening other review checks.

## 3. Collection and documentation

- [x] 3.1 Implement Collection emits the frozen reviewer policy in `collect`, keeping incomplete observations/verdict and the Pi/high default when nothing is frozen. Verify the collection regression tests and no-acceptance-invention behavior.
- [x] 3.2 Update `pi-skill/acceptance/reference.md` and `pi-skill/acceptance/contract.example.json` for the optional `reviewer` field and the frozen-medium rule.

## 4. Verification and delivery

- [x] 4.1 Run the exact frozen RED/GREEN command, Ruff on changed Python and `openspec validate allow-frozen-reviewer-policy --strict`; record requirement-to-evidence mapping.
- [ ] 4.2 Obtain a source-current independent review, resolve blocking findings, then commit and integrate to `dev` and hand off In Review; no `main` promotion or push without separate approval.
