# All-harness Headroom adaptation audit

## Scope

Task branch `task/slim-all-harnesses` adapts the Headroom sources from slim
`49ae15c` onto integrated dev `05c526f`. The integrated branch's retirement
preflight and four-harness wiring are retained; slim's Pi-only/GPT-only policy is
not copied into shared policy.

## Source and conflict decisions

- Ported pinned Headroom bridge, persistence, assets, requirements, install and
  Pi extension sources. Headroom stays local/offline at runtime; there is no
  provider proxy, API rewrite, automatic CC/Codex/OMP interception hook or model/
  thinking rewrite.
- Shared policy documents the matrix: automatic native Pi adapter versus explicit
  `megai headroom` CLI for CC, Codex and OMP.
- Retained dev retirement helpers and aggregate retirement metadata preflight.
  RTK, Caveman and agent-memory are no longer active installer/readiness defaults.
  Receipt-owned legacy assets are archived; ambiguous/custom registrations and
  nonempty daemon receipts refuse migration.
- Pi gets local owned skill copies plus an explicit shared-skill exclusion to avoid
  duplicate discovery. Provider/auth/model/thinking settings and explicit opt-outs
  remain user-owned.
- Plane Pi/Codex paths retain their existing shapes. CC and OMP use the verified
  `plane_mcp_remote.py` stdio bridge in `~/.claude.json` and selected OMP profile
  `mcp.json`; all requested targets are staged before mutation and target-bound
  backups support restore.

## Evidence run in this checkout

The earlier independent review marked commit `1bad4e8` **REQUEST CHANGES**. Its
candidate evidence is retained at `/tmp/megai-all-harness-acceptance.JcRvoB/logs`
(the baseline was SLIM, not this candidate; earlier references to a different
baseline path were stale). The candidate positives included distribution 27/1
skipped, Headroom wiring/runtime 11/11, Pi loader/extension, shared CLI,
performance, Plane lifecycle/cutover, orchestration, task autocreate, Ruff,
UX/UI and retirement gates. The candidate tgrep suite failed and was not claimed
as ready.

This correction adds fail-closed restore/retirement and memory-store checks,
selected-client launch verification, profile/path validation, remote-bridge
checks, transaction publication guards, tgrep readiness/freshness guidance and
Pi activation failure handling. Correction raw logs are retained under `/tmp/megai-correction-*`.

Follow-up review of `364e717` identified two remaining failures: directory
mutation during remove preflight and doctor checking only Pi registration. The
parent reproduced both as red regressions, then retained inert empty directories
while staging only receipt-owned files, and added an unconditional 30-second
local Headroom doctor probe separate from Pi activation. Removal/reinstallation,
dry-run immutability, and missing/failing runtime with Pi present/absent are covered.
Final parent logs: `/tmp/megai-all-harness-final.ygmVfy/logs` (including the red
regressions). Distribution 28, tgrep 34 (includes those 28), Headroom wiring 14 and
real runtime 11 pass without skips; Pi extension, Plane lifecycle/cutover,
retirement, policy, skill-kit and Ruff gates also pass. Final independent review
and exact delivery refs are recorded on the linked Plane item, not assumed here.

No live CC, Codex or OMP process was executed. No host installation, provider call,
Plane mutation by delegated agents or main promotion was performed. Ruff format remains a visible
check-only baseline difference; this audit does not claim formatting parity.

## Limits

Pi loader tests require an explicitly selected local Pi package. The local runtime
may read preinstalled public Headroom assets, but tests use disposable HOME,
MEGAI_HOME, Pi, Codex, OMP and XDG roots for writes. Runtime success does not
claim latency, token, billing or model-quality improvement.
