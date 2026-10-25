# Pi audit remediation

## Implemented, not assumed

- `workflow_checkpoint` accepts optional `repositoryPath`: an absolute, verified Git
  repository/worktree (or its subdirectory), or a configured coordination folder.
  Omit it in normal repo sessions and at ADAM/SPM-style coordination roots: existing
  `.pi/project.json` with `layout: "multi"` and a nonempty `repositories` list binds
  **all declared component repositories** automatically. The manifest takes precedence
  even if an unborn wrapper `.git` happens to exist. No root Git initialization,
  arbitrary child selection, recursive discovery or project-file rewriting occurs.
  Each component must be an independent committed Git root inside the coordination
  folder; missing, symlink, escaping, duplicate or invalid entries fail closed.
  Vector checkpoints include each component's HEAD/source digest and hashes of the
  manifest and optional root AGENTS.md. Drift anywhere requires reconciliation.
  Coordination scope is separate from component scope; legacy single-repo records,
  revision checks and explicit human knowledge approvals remain intact.
  For an unconfigured umbrella pass a relevant component path on **every** call.
  Manifest membership is authoritative, not exhaustive: undeclared sibling repos
  are not silently added. Resolve membership changes with the project owner.
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
Back up `~/.pi/agent/AGENTS.md` and the installed durable extension `index.ts` and
`store.mjs` in a private task receipt directory outside the source; record pre/post
SHA256 and modes. Verify installed pre-change bytes against the last receipt before
replacing them. Install exactly the reviewed profile, store and extension entry point. Preserve
settings, auth, MCP, sessions and unrelated extensions; do not run the broad installer.
Check installed hashes and run the real-loader suite with
`MEGAI_DURABLE_EXTENSION=/absolute/installed/megai-durable-workflow/index.ts`.
A running session may keep its original system prompt/tool schema: start a **new Pi
session** for the policy; `/reload` refreshes extensions but is not proof that the
original system prompt changed. Do not restart/kill somebody else's active session.
For rollback, restore ONLY those receipt-backed files after verifying their
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
