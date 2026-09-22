## 1. Freeze the Laya-only contract

- [x] 1.1 Rename and revise the existing OpenSpec artifacts for strict Laya-only source/profile scope, ordered branch consolidation and dev-only delivery; verify `openspec validate laya-only-pi-decisions --strict` passes.
- [x] 1.2 Freeze guarded acceptance commands for Laya behavior, workflow status, exhaustive tracked-source absence, active-profile absence and commit ancestry; verify the contract hash and criteria are recorded on the existing Plane item.

## 2. Consolidate applicable branch work

- [x] 2.1 Apply the three unique Laya refinement commits before unrelated work; verify their exact commits are ancestors of the candidate and focused Laya policy/default tests pass.
- [x] 2.2 Confirm the two installer-fix commits are patch-equivalent to `dev` and do not replay them; record the `git cherry` evidence.
- [x] 2.3 Apply the four workflow-status commits after Laya; verify their exact commits are ancestors of the candidate and focused workflow-status tests pass.
- [x] 2.4 Confirm the legacy-only branch tip and commits are not ancestors of the candidate and the source branch remains unchanged.

## 3. Remove the retired stack

- [x] 3.1 Delete every legacy-only tracked implementation, installer, prompt, test, benchmark, result, document and planning artifact while retaining the Laya-only OpenSpec change; verify tracked-path and tracked-content scans return zero matches.
- [x] 3.2 Remove migration-only names and behavior from mixed installer, model-policy, verification and test files; verify the Laya installer remains ownership-safe and focused tests pass.
- [x] 3.3 Update any affected package manifests or lockfiles only where they actively reference the retired stack; verify dependency installation and profile verification use no retired package.

## 4. Verify the committed candidate

- [x] 4.1 Run focused Laya runtime, policy, installer and active-scope suites; verify all assertions pass.
- [x] 4.2 Run focused workflow-status and safety suites; verify all assertions pass.
- [x] 4.3 Run Ruff on every changed Python file and strict OpenSpec validation; verify both exit zero.
- [x] 4.4 Commit the complete candidate and rerun exhaustive tracked-source scans plus branch ancestry/order checks against the exact commit; verify zero legacy matches and the required commit vector.

## 5. Guarded acceptance and dev delivery

- [ ] 5.1 Collect source-current acceptance evidence for the frozen criteria and inspect raw observations; verify the draft contains no missing or failed criterion.
- [ ] 5.2 Obtain one fresh independent read-only review of the exact commit and evidence, resolve blocking findings through the same writer, and verify a source-current PASS.
- [ ] 5.3 Reserve MEGAI `dev` through the integration queue, fast-forward the accepted task commit, verify the exact delivered SHA, and finish the reservation without pushing or touching `main`.

## 6. Apply the Laya-only local profile

- [ ] 6.1 Inventory affected active Pi resources and create a private timestamped backup outside the active profile; verify permissions and backup readability without copying session transcripts.
- [ ] 6.2 Remove only active retired extensions/prompts/configuration, run the delivered profile installer and reload verification; verify required Laya-backed tools load and the retired tool is absent.
- [ ] 6.3 Run an exhaustive active-resource scan excluding backups and sessions; verify zero legacy matches while existing backup/session data remains present.
- [ ] 6.4 Record repository SHA, local-profile evidence, review verdict, remaining risks and cleanup outcome on the Plane item, then hand off In Review and stop before `main` promotion.
