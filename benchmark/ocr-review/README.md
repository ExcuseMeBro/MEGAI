# OCR-delegation review benchmark — frozen preparation

Purpose: let the parent run a fair A/B pilot of **baseline Pi review** vs
**OCR delegation-assisted Pi review** (same reviewer model) over four small,
behaviour-verified changes. This commit only prepares and verifies the frozen
artifacts; it does not run reviews, score them, or adopt any integration.

## Scope note: delegation, not the native OCR engine

What is benchmarked is **`ocr delegate` only** — deterministic file selection
(`delegate preview`) and rule resolution (`delegate rule`). No OCR-side LLM,
provider or API key is involved. The native `ocr review`/`ocr scan` engine is
**not** part of this benchmark and was not run.

## Bullet summary

- **Verdict:** benchmark prep complete and frozen; four cases with
  ground-truth red/green verified (`OVERALL: OK`).
- **Reviewer-visible manifest:** `benchmark/ocr-review/manifest.json`.
- **Cases (base → candidate, all one Python file each):** `work/case-a`
  `af6280a`→`7e5fdc3`, `work/case-b` `3ce1383`→`d34d5e0`, `work/case-c`
  `42b11bd`→`7bdbaf4`, `work/case-d` `3ce1383`→`1299d4d`; rebuild with
  `fixtures/prepare_cases.py`.
- **Private truth / checks / logs (never reviewer-visible):**
  `private/ground_truth.json`, `private/verify_cases.py`,
  `private/logs/red-green.txt`, `private/logs/ocr-delegate-preview.txt`.
- **Pinned OCR CLI (task-local):** `@alibaba-group/open-code-review@1.12.4`,
  native binary `tools/ocr/node_modules/@alibaba-group/ocr-darwin-arm64/bin/opencodereview`,
  sha256 `b2944c8823075fd4edbedf521956d4893b4e973e5d47ed12f2f223cd21e792db`.
- **Runnable review commands:** see below; `delegate preview` and
  `delegate rule` verified working on all four cases (exit 0, no LLM endpoint).
- **Checks:** one behaviour-level check per case, run against both revisions;
  every case's expected base/candidate outcome is met. Raw log in
  `private/logs/red-green.txt`.
- **Answer-key check:** `delegate rule` resolves only the `system` Python rule
  for every case; no case repo carries a `rule.json`/`.opencodereview`, and no
  resolver token names a planted change.
- **Blockers/limitations:** small case set; the per-case origin/label mapping
  lives only in the private evidence directory.
- **Stopped here:** no reviews run, no Plane mutation, no integration, no live
  Pi/Paseo config change.

## Layout

```
benchmark/ocr-review/
  README.md                 this file
  manifest.json             reviewer-visible case metadata (no labels)
  SHA256SUMS                checksums of the frozen reviewer-visible artifacts
  briefs/review-brief.md    reviewer-visible brief, identical for both arms
  cases/case-<id>/
    base/...                frozen base snapshot (full source)
    change.patch            base -> candidate unified diff
  fixtures/
    prepare_cases.py        rebuilds work/case-* git repos from base + patch
    install_ocr.sh          task-local pinned OCR CLI install + checksum verify
  private/                  GITIGNORED answer key / checks / logs
  tools/, work/             GITIGNORED install + materialized repos
```

## Rerun

```sh
cd benchmark/ocr-review
./fixtures/install_ocr.sh          # task-local, pinned, checksum-verified
python3 fixtures/prepare_cases.py  # rebuild work/case-* git repos
python3 private/verify_cases.py    # PRIVATE red/green verification (expects OK)
```

## Exact review commands

Run per case from `benchmark/ocr-review` (`HOME` and telemetry isolation are
task-local only; delegation never calls an LLM):

```sh
OCR=tools/ocr/node_modules/@alibaba-group/ocr-darwin-arm64/bin/opencodereview
export HOME=/tmp/ocr-home OCR_ENABLE_TELEMETRY=0

# baseline arm: git only
git -C work/case-a diff base candidate

# OCR-delegation arm (same reviewer model drives step 3+ of the workflow)
"$OCR" delegate preview --format json --from base --to candidate --repo "$PWD/work/case-a"
"$OCR" delegate rule   --format json --repo "$PWD/work/case-a" lib/asana_plane_import.py
```

`delegate preview` reports mode/refs/merge_base and the reviewable file list;
`delegate rule` returns the resolved rule text grouped by content. Neither
touches a model or network endpoint. The same commands apply to `case-b`,
`case-c` (file `lib/acceptance_gate.py`) and `case-d`.

## Provenance and honesty

- Every case's origin and label is recorded in `private/ground_truth.json`,
  which is never reviewer-visible. Some cases replay real, verified MEGAI fix
  commits; at least one is a seeded change. The reviewer-visible tree, brief
  and manifest carry no label, defect description, scoring or check.
- The checks were re-derived from the frozen snapshots and independently
  reproduce the observed behaviour; they were not copied from the reviewed
  trees.

## Limitations

- Small case set with a single well-behaved change; the pilot cannot estimate
  a false-positive rate from it.
- The planted changes are narrow in shape, so the pilot does not cover every
  class of review finding.
- The OCR binary is installed per machine/arch; `fixtures/install_ocr.sh`
  pins and checksums the macOS arm64 artifact used here.
