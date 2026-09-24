## Context

Paseo MCP already accepts `notifyOnFinish` on `create_agent` and `send_agent_prompt`. A real read-only Pi reviewer READY completion reached the parent via notification on MEGAI-154. The repo-owned delegation guide is event-first but still advertises a bounded child wait; the installed local profile is Agy-first while repository policy and presets still favor DeepSeek. The `lib/pi_model_policy.py` transactional installer owns the relevant extensions and policy assets but preserves unowned local overrides.

## Goals / Non-Goals

**Goals:** Persist source-owned event handoff guidance and an opt-in reproducible Agy/GPT local profile, with focused offline installer/policy tests and a verified local installation.

**Non-Goals:** New daemon or subscription, changing Paseo's transport, treating Agy CLI as a Pi child, removing provider/CLI timeouts, sending credentials to Agy, switching active Pi sessions, or promoting/pushing main.

## Decisions

- Reuse native Paseo notification delivery rather than a custom Pi extension. Set `notifyOnFinish: true` on create and each background send; parent yields and correlates exact child/run events. The existing no-flag native wait is only a supported fallback; no artificial `--timeout`/sleep/status polling as a substitute for events. Preserve provider-stall limits.
- Add a separate `antigravity` installer preset while keeping explicit `economy` supported. The preset installs the schema-1 GPT roles without `economy`, sets fresh-session GPT defaults via the existing transactional staging path, and stages an empty `model-fallback.json` only for the explicit opt-in. Do not alter auth or other installed settings. The `megai-role-routing` extension already accepts a preset-free GPT role file.
- Source policy and extension wording reflect Agy as an eligible isolated worktree worker; native Pi/GPT coordinates and an independent Pi/GPT agent reviews. Existing Agy screening, `--sandbox`, no-commit/no-push/no-merge and permission behavior stay unchanged. Use repo-owned source bytes and focused tests instead of duplicating a second routing implementation.

## Risks / Trade-offs

- [Paseo notifications not connected to an arbitrary standalone Pi session] → verify the delivery path per parent and use a supported native wait or block; the opt-in flag alone is not proof.
- [No child-wait timeout while provider hangs] → preserve provider stall protection and reconcile the run before any writer replacement; parent may yield rather than block an indefinite shell call.
- [Installer refuses edited local policies as unowned] → back up complete current files and align repo source with reviewed installed bytes before installing; never overwrite unknown custom data or tamper with ownership receipts.

## Migration Plan

Commit and review only task-worktree changes, then apply the opt-in preset to the local Pi configuration with a private backup and focused read-back. On failure, keep the previous bytes and task branch for reconciliation. Rollback uses the private file backup; dev/main promotion remains independent of local installation.
