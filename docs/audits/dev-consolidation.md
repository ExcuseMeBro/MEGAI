# Dev consolidation conflict decisions

The user changed delivery from retained `pi`/`capy` workspaces to canonical `dev`,
with one primary workspace at rest and task-specific isolation during execution.
`main` promotion remains separately approved.

The `pi` fork diverged before newer `dev` ownership/retirement, shared-harness,
exact model-allowlist and provider-stall corrections. Preserve `dev` `f825f52` as
the runtime baseline rather than resurrecting retired tools or replacing native
configuration handling with the older Pi-only variant. Merge both histories and
port the complete acceptance/workspace feature delta `49ae15c..2669943`:
source/index-bound acceptance, schema-2 regression and collection flow, canonical
identity guard, receipt-owned Pi-only resource wiring and corresponding tests.
Existing CC/Codex/OMP behavior and newer Pi guards remain intact.

Old task refs `1b5fe0c` (GPT-only delegation) and `bb94008` (tgrep default) are
semantically superseded by the exact model guard/delegation policy and integrated
pinned tgrep installer/freshness contract. Retain their ancestry in a history-only
merge; do not reapply older policy or replace the corrected candidate tree.
The separately released Appllama addition `2669943..da5214c` is also integrated,
retaining its nine reviewed upstream/wrapper files and Pi-only receipt ownership.

Merge Capy `1cbf148` as the workflow/benchmark pack, retaining frozen starter files
and trial results. The unfinished acceptance-core files are superseded drafts;
retain their exact bytes privately, not over the hardened implementation. Preserve
the benchmark participant patch and regression privately before cleanup: publishing
or merging the solution into the starter would contaminate the pending comparison.

Source-bound verification must be captured again at the delivered primary before
its task checkout is archived. Historical receipts retain their original cwd and
are never rewritten to imply relocation. Cleanup requires released writers,
verified backups, merged ancestry, and supported Paseo archival, not registry edits.
