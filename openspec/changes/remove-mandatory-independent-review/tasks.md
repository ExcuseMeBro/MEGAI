## 1. Acceptance contract

- [x] 1.1 Add schema-3 review-free contract/collection/check support with focused red/green tests, preserving schema-1/2 review validation and failed/stale-check blocking; verify `python3 -m unittest discover -s tests -p acceptance_gate.py`.

## 2. Pi policy and distribution

- [x] 2.1 Remove separate-review steps and opt-in suggestions from Pi defaults, guarded acceptance, delegation and task-flow sources while preserving focused checks; verify scoped policy search and installer tests.
- [x] 2.2 Update the contract example/reference and adaptive docs to schema 3 and verify OpenSpec validation plus docs diff.

## 3. Source-current check

- [x] 3.1 Run focused acceptance, policy and Ruff checks and inspect the complete diff for acceptance and approval regressions before local dev delivery.
