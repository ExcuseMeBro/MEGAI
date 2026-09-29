## Verification

Evidence is source-current on the frozen worktree and contract. RED is the immutable
`red-2` receipt bound by the approved contract; the same command is the GREEN run below.

### Requirement-to-evidence mapping

| Requirement | Evidence |
| --- | --- |
| Frozen reviewer policy in schema-2 contracts | `tests/acceptance_gate.py::test_frozen_reviewer_policy_accepts_explicit_medium`, `test_malformed_and_schema_one_reviewer_policies_are_blocked`; `lib/acceptance_gate.py` `_contract` reviewer validation |
| Exact evidence validation against the frozen policy | `test_frozen_reviewer_policy_mismatch_is_blocked`, `test_legacy_contract_keeps_pi_high_reviewer_requirement`; `lib/acceptance_gate.py` `check` expected-policy comparison |
| Collection emits the frozen reviewer policy | `test_collect_emits_frozen_reviewer_policy_into_template`; `lib/acceptance_gate.py` `collect` draft review |

### Raw checks

- GREEN: `python3 -B tests/acceptance_gate.py -v` → `Ran 28 tests in 56.154s` / `OK`, exit 0.
- RED: `/Users/bro/.megai/acceptance/MEGAI-140/red-2/receipt.json`
  SHA256 `346f8e550b8b8f214fd949956f06afa993634718289ec8d0b65b3e375703244e`,
  exit 1, failure `AssertionError: 2 != 0 : {"status": "BLOCKED", "reasons": ["Unsupported contract schema"]}`.
- Ruff: `ruff check --no-fix --no-fix-only --force-exclude --no-cache -- lib/acceptance_gate.py tests/acceptance_gate.py`
  → `All checks passed!`, exit 0.
- OpenSpec: `openspec validate allow-frozen-reviewer-policy --strict` → valid, exit 0.
- `git diff --check` → clean, exit 0.

### Residual risk

Independent review, `dev` integration and the installed-CLI update remain open (task 4.2);
the RED baseline and frozen test file stay bound to the approved contract.
