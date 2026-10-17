# Saved local Pi profile

Baseline captured from `~/.pi/agent` on 2026-09-25 for MEGAI-168; model, thinking
and fallback fields were reconciled on 2026-10-06 for MEGAI-189. Other fields retain
the baseline, not a fresh live export. Role routing has been removed.
The installer does not apply this directory automatically.

- `settings.json`: selected model/thinking, per-model thinking, theme, packages,
  skill exclusions, retry and transport timeouts.
- `model-fallback.json`: provider fallback, independent of delegation.
- `models.json`: local provider definition and DeepSeek context overrides.
- `mcp.json`: lazy MCP configuration and the existing external credential helper.
- `web-search.json`: public research without browser cookies or automatic browser opening.

For restoration, compare with the destination first and merge only intended fields.
Expand `${HOME}` to the destination home; Pi need not expand this placeholder.
Supply `${PI_LOCAL_MODEL_BASE_URL}` and the local provider's omitted `apiKey` from
its own configuration. Preserve other providers, credentials and user settings.
Verify model availability; this snapshot is not a model catalog.

Authentication, trust grants, session history, model/MCP caches, installed packages
and backups are excluded. Saving these files does not switch an active parent.
No role file or routing extension should be restored. Direct parent execution is
the default; delegation follows task needs and explicit user choices.
