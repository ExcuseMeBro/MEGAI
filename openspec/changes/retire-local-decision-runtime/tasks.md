## 1. Delete the retired runtime from the tracked tree

- [x] 1.1 Remove every tracked artefact of the retired runtime: its Pi extension, stdio bridge, compaction companion, legacy compatibility extension, runtime installer, hash lock, shadow CLI, test fixtures, dedicated tests, its documentation page and the retired-tool-named OpenSpec change. Verified by the frozen zero-token path scan (`git ls-files`) and the content scan (`git grep`).
- [x] 1.2 Remove the extension staging and the runtime gate from `lib/pi_model_policy.py`, drop the retired runtime-preparation and profile-activation helpers from `pi-defaults/install.py` in favour of one fatal `apply_pi_policy` transaction, and drop the retired tool from the required tools in `pi-defaults/verify.mjs`. Verified by `python3 -B tests/pi_defaults.py`.

## 2. Retire installed assets safely

- [x] 2.1 Add `lib/retire_local_decisions.py` with exact-match retirement of the extension files, the saved state entry, the published source copies (recorded digests, including the `pi-profile` copy) and the owned pinned runtime, which moves into the private backups area. Verified by the new `tests/pi_model_policy.py` retirement tests: owned retirement, unowned file preserved, owned runtime moved, unowned runtime reported.
- [x] 2.2 Wire the published-source retirement into `lib/retire_legacy_sources.py` so `megai install`, the installer transaction and a plain reinstall all stage it through the shared plan and dry-run check. Verified by `tests/pi_model_policy.py`.
- [x] 2.3 Preflight pinned-runtime ownership before applying Pi policy/state, without moving it until the policy transaction succeeds. An unowned runtime now leaves the entire disposable profile unchanged; an owned runtime still moves after apply, while `--check` leaves it in place. TDD RED: `test_reinstall_reports_an_unowned_runtime_without_touching_it` failed on `self.assertEqual(self.snapshot(), before)` because `slim-wiring.json` and Pi resources changed. GREEN: the unowned and owned-runtime focused tests passed together (2/2). Residual: a runtime swap or backup/move failure after plan apply can still leave applied policy; retirement rechecks ownership before any move, so it does not move an unowned replacement.

## 3. Native decisions and compaction policy

- [x] 3.1 Rewrite the policy text so every workflow decision step is native judgment with no substitute compactor: `pi-defaults/AGENTS.md`, `pi-defaults/skills/pi-workflow/SKILL.md`, `pi-skill/ADAPTIVE.md`, `pi-skill/acceptance/SKILL.md`, `pi-skill/delegation.md`, `skills/agent-worktree-lifecycle/SKILL.md`, `task-flow/skills/megai-task-flow/SKILL.md` and `docs/pi-context-budget.md`. Verified by `tests/pi_adaptive_policy.py` and the native-compaction test in `tests/pi_model_policy.py`.
- [x] 3.2 Update the affected tests instead of weakening them: no runtime gate seam remains, retired-tool assets are asserted absent, and the new retirement behaviours are covered. Verified by the three frozen Python suites.

## 4. Model alias refresh

- [x] 4.1 Rewrite previous `gpt-5.6-*` alias spellings for those roles to `gpt-6-luna` / `gpt-6-sol` in active templates, economy preset, extension sources, tests, current documentation and OMP configuration; leave unrelated model generations untouched. Verified by the v3 active-content scan and `python3 -B tests/pi_deepseek_preset.py`.
- [x] 4.2 Restore twelve historical paths—benchmark records, protocol, audit, archived-policy examples and the tracked code-index snapshot—to exact base-commit bytes in both index and worktree. Verified by the v3 historical-evidence-preserved criterion; no older measurements are relabeled.

## 5. Local Claude install assets

- [x] 5.1 Delete the tracked repository-local `.claude/settings.json` plugin enablement; no repository-local `.claude` path is read by any source file, no history is rewritten and no path outside this repository is touched.

## 6. Verification and handoff

- [x] 6.1 Check all five v3 criteria after the runtime-preflight fix, Ruff on changed Python and strict OpenSpec validation; retain the earlier passing Node evidence. The separate opt-in context-budget native checks are blocked by the installed Pi 0.87.0 offline catalog not recognizing `gpt-6-sol`; do not silently skip them.
  Evidence: v3 SHA256 `b3c0c2059ccaa9156093d0e1220199c6276911c4b9c152159cdf50a532b827d8`; active-content scan PASS with historical `codedb.snapshot` restored; historical evidence 12/12 exact base bytes PASS; `tests/pi_model_policy.py` 61/61, `tests/pi_defaults.py` 25/25 and `tests/pi_deepseek_preset.py` 14/14 PASS; Ruff and strict OpenSpec validation PASS. Three directly affected Node integration tests previously passed and were not rerun after this Python-only fix. Native budget tests are not passing and were not skipped. The tracked snapshot has no retired-runtime token and is preserved as historical data; v3 excludes its earlier model aliases from the active-content scan.
- [ ] 6.2 Hand the source-current evidence to the parent for independent review and delivery; no commit, push, `main` promotion, archive or Git-history rewrite from the writer.
