## 1. Delete the retired runtime from the tracked tree

- [x] 1.1 Remove every tracked artefact of the retired runtime: its Pi extension, stdio bridge, compaction companion, legacy compatibility extension, runtime installer, hash lock, shadow CLI, test fixtures, dedicated tests, its documentation page and the retired-tool-named OpenSpec change. Verified by the frozen zero-token path scan (`git ls-files`) and the content scan (`git grep`).
- [x] 1.2 Remove the extension staging and the runtime gate from `lib/pi_model_policy.py`, drop the retired runtime-preparation and profile-activation helpers from `pi-defaults/install.py` in favour of one fatal `apply_pi_policy` transaction, and drop the retired tool from the required tools in `pi-defaults/verify.mjs`. Verified by `python3 -B tests/pi_defaults.py`.

## 2. Retire installed assets safely

- [x] 2.1 Add `lib/retire_local_decisions.py` with exact-match retirement of the extension files, the saved state entry, the published source copies (recorded digests, including the `pi-profile` copy) and the owned pinned runtime, which moves into the private backups area. Verified by the new `tests/pi_model_policy.py` retirement tests: owned retirement, unowned file preserved, owned runtime moved, unowned runtime reported.
- [x] 2.2 Wire owned published-source retirement through `retire_legacy_sources.py`, `install_slim_source.py` and Pi `slim_wiring.py`; finalize the runtime move after successful journaled `install_transaction.py --wiring-only` verification. Disposable-home source-publication, direct wiring and late-failure transaction tests are green.
- [x] 2.3 Preflight owned runtime and Plan destinations; direct Pi wiring atomically moves the runtime before Plan apply and restores it if policy publication fails, while a journaled installer defers the move until all phases pass. `--check` never moves it. TDD RED: injected move failure changed policy/receipt/state despite a nonzero exit (`/tmp/m145_move_red.log`); GREEN: move-failure and post-move policy-failure snapshots match the original disposable profile (`/tmp/m145_move_green.log`, `/tmp/m145_rollback_focus.log`). Residual: a process crash between a direct rename and Plan apply requires manual recovery from the preserved backup; concurrent edits can also block journal rollback.

## 3. Native decisions and compaction policy

- [x] 3.1 Rewrite the policy text so every workflow decision step is native judgment with no substitute compactor: `pi-defaults/AGENTS.md`, `pi-defaults/skills/pi-workflow/SKILL.md`, `pi-skill/ADAPTIVE.md`, `pi-skill/acceptance/SKILL.md`, `pi-skill/delegation.md`, `skills/agent-worktree-lifecycle/SKILL.md`, `task-flow/skills/megai-task-flow/SKILL.md` and `docs/pi-context-budget.md`. Verified by `tests/pi_adaptive_policy.py` and the native-compaction test in `tests/pi_model_policy.py`.
- [x] 3.2 Update the affected tests instead of weakening them: no runtime gate seam remains, retired-tool assets are asserted absent, and the new retirement behaviours are covered. Verified by the frozen Python suites.
- [x] 3.3 Remove the stale file-selection companion from `pi-defaults/verify.mjs` and `pi-defaults/AGENTS.md`; use native scoped path/search selection. RED: source contract and actual disposable Pi loader both reported the missing tool (`/tmp/m145_sift_red_py.log`, `/tmp/m145_sift_red_node.log`); GREEN: both checks pass with no mandatory loader tool missing or extension error (`/tmp/m145_sift_green_py.log`, `/tmp/m145_sift_green_node.log`).

## 4. Model alias refresh

- [x] 4.1 Rewrite previous `gpt-5.6-*` alias spellings for those roles to `gpt-6-luna` / `gpt-6-sol` in active templates, economy preset, extension sources, tests, current documentation and OMP configuration; leave unrelated model generations untouched. Verified by the v3 active-content scan and `python3 -B tests/pi_deepseek_preset.py`.
- [x] 4.2 Restore twelve historical paths—benchmark records, protocol, audit, archived-policy examples and the tracked code-index snapshot—to exact base-commit bytes in both index and worktree. Verified by the v3 historical-evidence-preserved criterion; no older measurements are relabeled.

## 5. Local Claude install assets

- [x] 5.1 Delete the tracked repository-local `.claude/settings.json` plugin enablement; no repository-local `.claude` path is read by any source file, no history is rewritten and no path outside this repository is touched.

## 6. Verification and handoff

- [x] 6.1 Recheck all five frozen v3 criteria, affected distribution/transaction suites, actual disposable Pi loader, Ruff on changed Python, strict OpenSpec validation and `git diff HEAD --check`. The separate opt-in context-budget native checks remain blocked by installed Pi 0.87.0's offline catalog not recognizing `gpt-6-sol`; no native assertion was skipped.
  Evidence: v3 SHA256 `b3c0c2059ccaa9156093d0e1220199c6276911c4b9c152159cdf50a532b827d8`; active-content scan PASS; twelve historical paths including `codedb.snapshot` preserve base bytes. Frozen suites: `tests/pi_model_policy.py` 63/63, `tests/pi_defaults.py` 25/25, `tests/pi_deepseek_preset.py` 14/14. Affected `tests/headroom_wiring.py` 15/15 and `tests/slim_distribution.py` 45/45. Actual Pi loader checks `tests/pi-defaults-tools.mjs` and `tests/pi-model-guard.mjs` PASS with `PI_PACKAGE_ROOT` set; Ruff (eight changed Python files), strict OpenSpec and diff check PASS. Normal exceptions recover runtime and policy; an abrupt crash between standalone rename and Plan apply or a concurrent rollback conflict still requires manual recovery from preserved backups.
- [ ] 6.2 Hand the source-current evidence to the parent for independent review and delivery; no commit, push, `main` promotion, archive or Git-history rewrite from the writer.
