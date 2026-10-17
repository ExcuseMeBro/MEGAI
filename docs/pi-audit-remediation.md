# Pi audit remediation

## Implemented, not assumed

- `workflow_checkpoint` accepts optional `repositoryPath`: an absolute, verified Git
  repository/worktree (or its subdirectory). Omit it in a normal repository session.
  In an umbrella session pass it on **every** checkpoint call. Invalid/relative paths
  fail without fallback or repository creation. Existing revision, source-drift,
  repository scoping and human knowledge-approval checks are unchanged.
- Save requires `uncertainOperations`, explicitly `[]` when no mutation is uncertain.
  Unsupported checkpoints are reported once, not retried unchanged. A non-Git runtime
  task must not select an unrelated Git repo just to get a checkpoint.
- `pi-defaults/local-profile/minimal-AGENTS.md` is an **opt-in runtime profile**, not a
  replacement for repository instructions or a change to the general installer.
  It retains tracking/isolation/queue/approval/verification restrictions, removes
  repetition and adds bounded reads and reuse-until-drift guidance. No hooks,
  background automation, extra skills, model hopping or new dependencies.
- `scripts/pi_session_metrics.py` reads JSONL metadata only and prints aggregate JSON.
  It excludes the current Pi session by `PI_SESSION_ID` and `PI_SESSION_FILE`, filters
  each entry by timestamp (not file mtime), bounds individual input lines, and skips
  symlink files. It does not alter history or output prompts, tool arguments, raw
  errors, arbitrary tool names or file paths. Keep even aggregate reports private.

```sh
python3 scripts/pi_session_metrics.py --days 7
# Compare fixed windows with --until timezone-aware-ISO; --sessions selects a test directory.
```

Counts are **session-level**, not user-task completion times or proof of improved
productivity. A user task may span sessions, while one session may contain many tasks.
The direct Plane/checkpoint percentage does not attribute nested bash/orchestration.
`durationMs` samples may be missing and are not first-token or end-to-end user latency.
Cache percentage is cacheRead / (input + cacheRead), only where usage fields exist.
Oversized/inaccessible records are counted as skipped; incomplete data is not an
absence claim. No historical numeric report or private session transcript is shipped.

## Selective local application and rollback

Only apply after reviewing the complete diff and passing focused acceptance.
Back up `~/.pi/agent/AGENTS.md` and the installed durable extension `index.ts` in a
private task receipt directory outside the source; record pre/post SHA256 and modes.
Confirm installed extension store bytes match this source before replacing its entry
point. Install exactly the reviewed profile and extension entry point. Preserve
settings, auth, MCP, sessions and unrelated extensions; do not run the broad installer.
Check installed hashes and run the real-loader suite with
`MEGAI_DURABLE_EXTENSION=/absolute/installed/megai-durable-workflow/index.ts`.
A running session may keep its original system prompt/tool schema: start a **new Pi
session** for the policy; `/reload` refreshes extensions but is not proof that the
original system prompt changed. Do not restart/kill somebody else's active session.
For rollback, restore ONLY those two receipt-backed files after verifying their
current bytes are still the installed post-change hashes. Never overwrite later
operator changes. Keep private backups; do not commit them.

## Transport A/B: measure before changing configuration

The audit does not establish that billion-context, Pi, the provider or network is
the latency bottleneck. No transport/package/model switch is automatically applied.
Keep the selected provider/model/thinking, auth, prompt and tool set identical.

1. Use an operator-approved isolated test session/configuration; keep all auth private
   and out of shell arguments, reports and Git. Do not edit the live shared settings.
2. A = current configuration with billion-context; B = only that package's extension
   disabled through Pi's package resource configuration. Do not disable every
   extension or substitute a model/provider: those would confound the comparison.
3. Run at least 5 paired identical bounded read-only prompts, alternating A/B order.
   Separate cold starts from warm requests. Record failures, first-token and total
   wall times, tool counts, input/cache/output usage and configuration provenance.
   Session `durationMs` alone cannot supply first-token timing.
4. Compare median and p95 within cold/warm groups. Inspect failed trials rather than
   dropping them. Treat small samples as exploratory, not a promised speedup.
5. Restore the test configuration; apply a persistent transport change only after a
   clear measured benefit and explicit approval of its trade-offs. Preserve the
   private pre-change receipt. No invented A/B results or model access assumptions.
