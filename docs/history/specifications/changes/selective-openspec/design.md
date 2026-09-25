## Context

MEGAI already owns Asana, `.todos`, worktrees, model routing and verification. OpenSpec must supply durable requirements, not replace those controls. Pi discovers global skills on demand, so generating a second bundle of project OPSX skills/prompts is unnecessary for this integration.

## Goals / Non-Goals

Goals: selective planning, bounded child context, one detailed checklist, explicit evidence, safe opt-in installation.
Non-goals: orchestration engines, mandatory specs for small fixes, all-project initialization, remote stores, model changes, automatic archive or main promotion.

## Decisions

- Reuse upstream `spec-driven` schema and CLI JSON instructions; do not implement a custom schema or parser.
- One `megai-openspec` global Pi skill owns selection and lifecycle policy. Install via a standalone optional Bash script, outside `lib/main.sh`.
- Initialize MEGAI with `--tools none`; users invoke `/skill:megai-openspec` or let its trigger select it. Existing native OPSX integrations remain untouched and must follow the same parent boundaries.
- Pin 1.12.0, use `--ignore-scripts`, disable telemetry before operational calls, and record installed version in existing MEGAI state. Reject mismatched existing versions rather than silently upgrading/downgrading.
- `openspec/config.yaml` supplies project facts and artifact rules. It is advisory, not an enforced security/test gate. Parent acceptance and real tests stay authoritative.
- Keep this change active during In Review. A checked checklist records implementation evidence, not permission to archive or mark Asana Done.

## Risks / Trade-offs

The CLI adds a Node dependency; install is opt-in and requires >=20.19.0. Spec generation costs tokens, so small fixes bypass it and only relevant artifacts are passed to children. Prompt rules cannot guarantee model compliance; shell tests verify installer behavior, real CLI checks verify contracts, and the five-task pilot records quality/latency evidence without claiming causality. This rollout changes pilot conditions and is labelled separately from later stable-policy tasks.

## Rollback

Run `bash "$HOME/.megai/lib/install_openspec.sh" --remove` to unlink only MEGAI's owned Pi skill. Keep CLI/privacy configuration and project artifacts for audit; remove or revert them only through an explicit repository change. The existing orchestration workflow remains usable throughout. `megai uninstall` invokes the same safe unlink before deleting MEGAI home.

## Verification

Installer sandbox: fresh/repeated install, exact npm flags, telemetry env, state, user-file/link collision, incompatible CLI, owned removal and repository preservation. Real CLI: validate this spec, inspect injected context/operation guidance, and prove that planning completion differs from task completion. Existing Pi task-flow and orchestration-policy regressions remain required.
