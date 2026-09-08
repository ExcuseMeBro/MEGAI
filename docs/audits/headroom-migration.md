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

- Local Headroom runtime: `tests/headroom_runtime.py`, 11/11 pass using the
  explicitly selected installed interpreter/assets; raw log: parent-provided
  `/tmp/megai-headroom-baseline.vJK40b/runtime.log`.
- Headroom wiring and distribution tests are being adapted from their original
  slim Pi-only fixtures for the four-harness contract. Their current raw logs are
  kept outside the repository while implementation proceeds.
- Shell syntax, Python compilation and `git diff --check` are run after edits.
- No CC, Codex or OMP process was executed. No host installation, provider call,
  Plane mutation or main promotion was performed.

## Limits

Pi loader tests require an explicitly selected local Pi package. The local runtime
may read preinstalled public Headroom assets, but tests use disposable HOME,
MEGAI_HOME, Pi, Codex, OMP and XDG roots for writes. Runtime success does not
claim latency, token, billing or model-quality improvement.
