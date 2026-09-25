## Context

See proposal.md and specs/native-pi-routing/spec.md. The current installer owns an Agy extension and an opt-in preset that writes GPT-only roles plus an empty fallback map. Role guidance is prompt-only; the existing model-fallback extension changes a failed Pi session's model but currently preserves its prior thinking level. The shared primary dev checkout has unrelated tracked dirt; task writes stay in the Paseo-managed branch.

## Goals / Non-Goals

**Goals:** Restore native Pi execution and a single, verified high-thinking Luna recovery on DeepSeek balance exhaustion, without a broad provider bypass.

**Non-Goals:** Removing the system-wide `agy` executable or credentials, automatic payment/top-up, main/push, stealing another owner's dirty checkout, or promising a fallback when Luna is unavailable.

## Decisions

1. Reuse the existing installer ownership ledger and native Pi role/fallback extensions. Replace the active Agy preset with an explicit GPT-coordinator/DeepSeek-worker profile; keep the existing economy option independent. Retire only owned Agy extension and Agy-specific prompt sections rather than modifying unrelated Pi resources. Avoid an extra daemon or a custom provider.
2. Configure DeepSeek Flash → GPT Luna as the only recovery edge. At an authenticated provider-specific insufficient balance, preserve the live follow-up path and explicitly set Luna's supported thinking to `high` after a successful model switch. The parent quiesces/reconciles a separate child before any replacement; no background parallel writer. Do not treat permission or shared quota as a balance error.
3. Update focused offline tests first to prove Agy resources disappear, native roles appear and the fallback occurs exactly once at `high`. Keep existing negative cases. Verify the source-current diff, targeted tests and an independent GPT security review before scoped runtime installation.

## Risks / Trade-offs

- [Provider balance can be unavailable at test time] → offline tests assert routing; live provider validation records its actual outcome, without triggering a paid action.
- [Agy policy installed in unrelated or unowned files] → preflight ownership and private backups; fail closed rather than overwrite.
- [The integration queue rejects dirty primary dev] → preserve it, finish source verification in the isolated checkout and report the delivery hold rather than falsify a reservation.

## Migration Plan

Preview owned installer changes, verify backup/ownership and apply only after final source review. Keep backups for rollback to the exact original local config. New sessions use the profile; existing sessions keep their selected model until restart/reload. Do not delete the user's standalone Agy CLI.
