# Saved local Pi profile

Captured from `~/.pi/agent` on 2026-09-25 for MEGAI-168. These are the user's
current preferences, separate from the optional shared presets. The installer
does not apply this directory automatically.

- `settings.json`: selected model/thinking, per-model thinking, theme, packages,
  skill exclusions, retry and transport timeouts.
- `megai-roles.json` and `model-fallback.json`: current role identities and fallback.
- `models.json`: local provider definition and DeepSeek context overrides.
- `mcp.json`: lazy MCP configuration and the existing external credential helper.
- `web-search.json`: public research without browser cookies or automatic browser opening.

For restoration, compare with the destination first and merge only intended fields.
Expand `${HOME}` to the destination home; it is a documentation placeholder, not
an assumption that Pi expands it. Supply `${PI_LOCAL_MODEL_BASE_URL}` and the local
provider's omitted `apiKey` from the destination's own configuration. Preserve
other providers, credentials and user settings. Verify model availability before
choosing this profile on another machine; this snapshot is not a model catalog.

Authentication, trust grants, session history, model/MCP caches, installed packages
and backups are intentionally excluded. No live model preference is changed by
saving this profile. Managed instructions and slash commands live in the sibling
`AGENTS.md`, `skills/` and `prompts/` sources; preserve custom local additions when
updating them. The active Pi policy uses parent self-review even though the saved
roles retain the user's reviewer entry.
