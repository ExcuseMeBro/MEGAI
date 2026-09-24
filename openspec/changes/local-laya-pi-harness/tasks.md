## 1. Preserve and contract

- [ ] 1.1 Verify `archive/megai-156-jev-config` points to the baseline Jev source SHA and the installed extension hashes match; record branch and local private-backup paths in the Plane item (no remote push).
- [ ] 1.2 Freeze a guarded acceptance contract outside the worktree, store its hash on the Plane item, and verify `openspec validate local-laya-pi-harness --strict` succeeds before source implementation.

## 2. Local runtime and typed tool

- [ ] 2.1 Write failing focused bridge tests for real typed `choice`/`score`/`noul` wire shapes, complete-token rejection, malformed output, EOF and timeout without hosted network; verify the tests fail on the missing local bridge.
- [ ] 2.2 Implement a pinned Laya multilingual Python stdio bridge with on-demand model load, bounded private JSON-lines I/O and a deterministic local test backend; verify bridge tests pass and a real MPS smoke call identifies the multilingual checkpoint.
- [ ] 2.3 Write failing Pi adapter tests for `laya`, file screening, absent hosted Jev credentials/traffic, advisory tool-call flow and runtime crash recovery; verify the missing adapter fails then implement it with one session-owned subprocess and passing tests.

## 3. Compaction and browser retirement

- [ ] 3.1 Write failing compaction tests for local short-input handling, tokenizer-detected overflow, no safe reduction, explicit instructions and crash fallback; implement loss-avoiding local handling with native Pi summarization on every unsafe path, and verify tests pass.
- [ ] 3.2 Remove the active Jev-browser skill/executable wiring and old hosted Jev extension sources from the migration branch while preserving them on the backup branch; verify the disposable Pi loader exposes `laya` but no active Jev or Jev-browser capability.

## 4. Owned installation and delivery

- [ ] 4.1 Write failing installer tests for first install, exact receipt-owned Jev retirement, preservation of operator-edited assets, missing/unowned runtime, `--check` and unchanged Pi native model settings; implement the smallest ownership-safe Laya runtime/wiring changes and verify focused Python suites pass.
- [ ] 4.2 Update only active policy/docs and executable checks that name the retired hosted interface; verify no active TypeSafe endpoint/key use remains, browser skill is absent, and historical specs/evidence stay intact.
- [ ] 4.3 Run focused Python/Node tests, strict OpenSpec, Ruff on changed Python, `git diff --check`, a disposable offline Pi loader and a real local MPS smoke test; commit owned task changes, then capture source-current guarded acceptance and independent security/data-integrity review.
- [ ] 4.4 With private backup and ownership verified, install to the scoped local Pi profile, inspect a newly loaded Pi session, then reserve and fast-forward local dev only if its dirty/unrelated state and moved remote base can be reconciled without overwrite; record exact delivery or blocker in the same Plane item and leave main/push untouched.
