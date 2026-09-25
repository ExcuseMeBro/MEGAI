## Why

The operator explicitly wants no hosted Jev calls in the local Pi harness and wants the current Jev configuration recoverable on a separate local branch. The Laya multilingual model can provide on-device typed decisions, but measured agreement with Jev on English project decisions was only 51.2%; the migration must not silently reuse Jev's calibrated blocking thresholds or discard long compaction history.

Plane project/work item: `59005e36-ecd4-46ed-bb42-f779858b20ce` / `5989119a-57f9-437b-9ba6-2ca70d81be8c`.

## What Changes

- Preserve the current committed Jev Pi source as `archive/megai-156-jev-config` at `2c3896cc990cecd2816b9b61a069f8dedda669da`; preserve separately owned installed configuration in a private backup. No secrets or operator-edited files enter the branch.
- Replace the hosted Jev Pi decision, file-screening, and compaction integrations with local Laya multilingual inference. **BREAKING:** the hosted Jev endpoint/key are no longer consulted; prior Jev-specific tool calls and thresholds are not guaranteed to have the same results.
- Never block tool calls based on Jev-tuned thresholds applied to uncalibrated Laya output. Preserve Pi's native permission handling. On Laya failure, invalid/overlong input, or compaction with no safe reduction, retain content and use Pi's native summarization rather than lose context.
- Disable the Jev-browser skill and executable from the active local Pi profile. Document that browser automation is unavailable until a separately approved local replacement exists.
- Install the pinned local Laya runtime with ownership-checked, reversible Pi policy wiring, and test both the source and the installed local profile without modifying Pi's selected provider/model/thinking.

## Capabilities

### New Capabilities

- `local-pi-decisions`: On-device typed decisions, local file relevance, safe tool-call advice, and loss-avoiding compaction fallback in the Pi harness.
- `owned-local-runtime`: Ownership-checked Laya runtime installation and retirement of only owned hosted Jev assets, with private backups and no credential deletion.

### Modified Capabilities

None: `openspec/specs/` has no main capability specs. This change explicitly supersedes the conflicting native-only decision/compaction requirements proposed in the unarchived `retire-local-decision-runtime` change; preserve that change and its historical evidence rather than rewriting it.

## Impact

`pi-skill/jev/index.ts`, `pi-skill/jev-compaction/index.ts`, `lib/pi_model_policy.py`, the Pi installer/wiring and local runtime entry point, `pi-skill/jev-browser/`, `bin/jev-browser`, the adaptive policy and focused Pi extension/installer tests. Installed scope: receipt-owned `~/.pi/agent/extensions`, owned skill/CLI assets, and one privately backed-up local Laya environment; not the user's credentials, unrelated settings, caches, or sessions. No push, main promotion, provider switch, new background daemon, or external Laya inference service. Source delivery targets local dev only after formal acceptance and independent review; the backup branch remains local and retained.
