## Context

See proposal.md. The installed Jev extensions are byte-identical to the committed sources on `dev` at `2c3896cc990cecd2816b9b61a069f8dedda669da`; that SHA is now retained in the Paseo-managed `archive/megai-156-jev-config` worktree. The primary `dev` checkout has an unrelated dirty `codedb.snapshot` and is two commits behind its remote. The earlier, unarchived `retire-local-decision-runtime` OpenSpec change chose native-only decisions; the operator's new explicit choice supersedes that proposal, not its history.

## Goals / Non-Goals

**Goals:** No active hosted Jev path, durable local Laya inference, no uncalibrated tool-call blocking or compaction data loss, existing ownership-safe installer behavior, source and installed-profile recovery.

**Non-Goals:** Replacing Pi's chat model with Laya, guaranteeing equivalent Jev answers, producing arbitrary summaries with a non-generative model, retaining Jev-browser automation, deleting credentials or cache, changing the operator's model/thinking settings, pushing or promoting to main.

## Decisions

### Retain the original revision as a separate branch

The Paseo-managed local branch `archive/megai-156-jev-config` points at the exact committed `dev` SHA whose Jev extension hashes match the installed files. It is retained, not fast-forwarded with the migration or published. Non-Git installed bytes and ownership receipts need a separate private backup: a Git branch cannot contain them safely. The new task worktree starts from the same local `dev` SHA, not the dirty checkout.

### One local model process with private stdio

Replace the Jev extension with a small TypeScript Pi adapter and a session-owned Python JSON-lines bridge using pinned `laya-multilingual` on MPS. Start the Python process lazily on a request, not at extension load or as a daemon; reuse it for typed decisions, sift and compaction; serialize requests to prevent MPS contention; close on session shutdown and EOF. Bound message sizes, timeouts and JSON parsing. Never execute text returned by the model or forward prompts to a remote service. The Python bridge validates the complete tokenized sequence against the checkpoint's context, rather than estimating its size by characters; it must reject truncation before inference. A finite, normalized answer distribution is required for every question. A crash or timeout returns an explicit error and leaves Pi's own permission path unchanged.

Considered loopback HTTP (`laya-serve`): rejected because an unattended listener, port collisions and ambiguous process ownership are unnecessary. Considered launching a new Python interpreter per request: rejected because checkpoint load is orders of magnitude slower than steady-state inference.

### Treat model judgments as advisory until calibrated

The historical Jev gate thresholds were fitted on Jev and MUST NOT block tools or redirect agent calls when applied to Laya. Remove those blocking hooks; Pi's own permissions remain authoritative. Retain local decision and sift tools for explicit calls, with old `jev` tool name retired and a new `laya` identity. Caller-visible errors explain the new limits; no automatic hosted fallback. Session logs record only bounded metadata, never prompt text or keys. Code and docs must not advertise the uncalibrated output as equivalent to Jev.

### Conservative compaction

The compaction extension calls the same local bridge only when its complete state and question branches fit the checkpoint. It cannot trust the old Jev `0.5` drop threshold. It retains all original entries unless a reduction is independently lossless (for example, a duplicate tool result already retained with the same bytes); in every other case it returns `undefined` and lets Pi's native summarizer run. An explicit `/compact` instruction, overflow recovery, invalid output or no meaningful reduction also falls through. The raw session log is never rewritten. Considered automatic model-only dropping: rejected because the 1024-token model has not demonstrated reliability on long, security-relevant project histories.

### Ownership-safe install and rollback

Extend the existing `Plan`/receipt and private backup transaction rather than hand-editing shared Pi files. Stage new owned extensions and bridge, retire exact receipt-owned Jev extensions and browser skill; unowned/modified files block migration rather than being overwritten. Install a pinned Laya venv in one clearly owned non-Git directory (without saving secrets); preflight its marker/ownership before any move. The installed profile receives no TypeSafe API key use, listener or automatic service. `--check` is read-only; verify real loader on a disposable profile, then privately back up local owned settings/assets and apply. Reinstall source publishes safely; rollback uses the retained Git branch and local private backups. The current already-running Pi session may require `/reload` or a new session; a successful file install is not proof of live-session activation.

## Risks / Trade-offs

- **Different decisions** → On English real project sessions Laya multilingual matched only 51.2% of Jev `choice` outputs; keep judgments advisory, report disagreement and do not promise parity.
- **Long context and information loss** → Tokenize before inference; native Pi summarization is the safe fallback, never a model-only deletion of unique evidence.
- **Cold start and memory** → Load the checkpoint once per Pi session on first use; expose cold-start and RAM/MPS usage in runtime checks, not as a guaranteed latency.
- **Installer conflicts / crash** → Use receipt checks, atomic staging and private backups; stop on uncertain state; do not force-remove or repair an operator-edited file.
- **Missing browser replacement** → Disable the Jev-browser skill and executable from the active profile; do not silently keep a hosted route under a new name.
- **Existing OpenSpec conflict** → Keep the previous unarchived native-only change intact; this new delta records the operator's updated decision. Do not archive either change or modify main specs without separate authorization.

## Migration Plan

1. Freeze acceptance in the Plane task and in private contract evidence; require source-current independent security/data-integrity review.
2. Implement in `task/megai-156-local-laya` with test-first focused cases for IPC, complete-token rejection, tools, compaction fallback and ownership-safe installation. Verify an offline Pi loader and one real local MPS decision.
3. Commit reviewed source; install to an explicitly owned local Pi configuration scope only after private backup and read-back of unaffected settings. Verify no active hosted Jev tools or browser skill and that a new Pi session loads the local tool.
4. Integrate source to local dev only when the primary checkout's unrelated dirty state and moved remote base can be safely reconciled; never reset or overwrite it. Keep the Jev archive branch and private backup. Main/push require later explicit approval.
