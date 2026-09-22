## 1. Test contract and migration surface

- [ ] 1.1 Add failing tests for an installed `laya` tool, absent `jev` tool, mixed typed answers, one reused local bridge process and bounded local failures; verify the focused test fails because the Laya extension does not yet exist.
- [ ] 1.2 Add failing installer tests for pinned runtime ownership, supported-platform checks, new Laya assets and retirement of owned `megai-jev*`; verify they fail against the current installer.

## 2. Local runtime

- [ ] 2.1 Add the Python JSONL bridge with one `Router(max_loaded=2)`, lazy English/multilingual retention, optional request `lang`/operator `LAYA_LANG`, no typed-decisions route, and one sanitized response per request; verify deterministic bridge protocol tests cover both routes, model/process reuse, malformed input and inference errors.
- [ ] 2.2 Add pinned upstream `laya==0.3.5` runtime preparation (owned venv, pinned interpreter, hash lockfile, selective English/multilingual checkpoint verification) and ownership checks; verify installer tests and a clean prepare-only install succeed on Darwin arm64, and that `LAYA_DEVICE`, `LAYA_PYTHON` and optional `LAYA_LANG` are honoured.

## 3. Pi decision extension

- [ ] 3.1 Replace `pi-skill/jev` with `pi-skill/laya`, retaining bounded validation, local ledger, cancellation and fail-open semantics; verify focused tool tests pass with a fake bridge and no TypeSafe environment/key access.
- [ ] 3.2 Port sift, gate/router and failed-tool guidance to the shared local runtime, default gate blocking off and explicit blocking on; verify path/privacy, route, repair, report-only and repeat-unchanged tests pass.
- [ ] 3.3 Replace Jev compaction with Laya compaction and local-runtime imports; verify failed batches keep content and valid batches preserve the existing compaction contract.

## 4. Wiring and active policy

- [ ] 4.1 Update ownership-aware installer wiring to install `megai-laya*`, include the bridge, retire owned `megai-jev*`, and use the Laya runtime installer; verify policy/install integration tests pass.
- [ ] 4.2 Rename the active decision ledger helper and active Pi policy/skills/docs from Jev to Laya while preserving historical benchmark artifacts; verify exhaustive active-scope search finds no TypeSafe runtime/key/endpoint dependency or executable `jev` tool.

## 5. Verification and delivery

- [ ] 5.1 Run changed Python Ruff, focused Node/Python/shell suites and OpenSpec strict validation; verify every command exits zero with observed assertions.
- [ ] 5.2 Run English and Uzbek-hinted `choice`/`score`/`noul` requests through one real installed bridge, observe English and multilingual routing with no reload/typed-decisions model, verify no hosted TypeSafe request/credential is used, and record model/timing without input text.
- [ ] 5.3 Obtain source-current independent guarded review, resolve blocking findings, then rerun affected checks and verify acceptance PASS.
- [ ] 5.4 Commit the complete change, push non-force to `origin/pi-laya`, verify the exact remote head, record the receipt/evidence in Plane and hand off In Review without changing `dev` or `main`.
