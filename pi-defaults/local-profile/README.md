# Saved local Pi profile

Baseline captured from `~/.pi/agent` on 2026-09-25 for MEGAI-168. Model, thinking,
role and fallback fields were reconciled with the installed reviewed-hybrid profile
on 2026-10-06 for MEGAI-189. Other fields retain the baseline, not a fresh live export.
This saved profile is separate from optional shared presets; the installer does not
apply this directory automatically.

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
updating them.

## Reviewed-hybrid routing

GPT-6.1 Sol medium remains the parent and independent reviewer. DeepSeek Flash high
handles substantial bounded low-risk bugfix/refactor implementation; questions,
trivial changes, new features and security/data-integrity work stay with the parent.
The parent states its routing decision before implementation and reports the models
that actually ran. Worker output needs actual tests and fresh GPT review. A missing
launch/completion path, isolated workspace or reviewer is a reported blocker, not
permission to silently substitute GPT. Role files are guidance, not automatic dispatch.

Only a confirmed DeepSeek HTTP 402 insufficient-balance error permits one stopped-writer
continuation on GPT-5.6 Luna medium. Preserve prior diffs/evidence; authentication,
permission and uncertain-write failures need reconciliation. Saving these files does
not install an extension, reload existing sessions, change credentials or switch an
active parent. Install the reviewed `pi-skill/role-routing/index.ts` extension separately
and use `/reload` in an idle session. New sessions load it automatically.
