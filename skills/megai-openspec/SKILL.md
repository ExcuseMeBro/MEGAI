---
name: megai-openspec
description: Parent-owned OpenSpec workflow for multi-module features, public API or data migrations, and explicit spec requests. Keep small known-seam fixes on the normal fast path; preserve Asana and test gates.
---

# Selective OpenSpec for MEGAI

OpenSpec is a requirements layer, not another orchestrator or a test runner. Apply this policy to native OPSX commands too. Repository rules and explicit user decisions remain authoritative.

## Choose the smallest path

- Use for multi-module behavior changes, public API/schema/data migrations, consequential security behavior, or an explicit spec request.
- A small known-seam fix, typo, or behavior-preserving local cleanup stays on the existing workflow: acceptance + diff + focused test. Do not initialize OpenSpec or generate artifacts for these tasks unless requested.
- Pure exploration is read-only until the user authorizes a change. No retrospective whole-repository spec generation, beta stores, extra agents, or automatic queue draining.

## Parent boundary and identity

Complete the existing `megai-task-flow` start boundary before any project writes, including `openspec init` and `new change`. Reuse the linked Asana GID; children never mutate Asana or `.todos`.

- Asana owns coordination/status. `.todos` holds one linked summary plus the change-directory path.
- OpenSpec owns requirements/design and the single detailed implementation checklist, `tasks.md`. Do not mirror individual tasks into Asana or `.todos`.
- Record the Asana GID in `proposal.md`; retain the change path in the task handoff. On resume read the linked change, not every spec or the entire chat.

## Prepare and agree

1. Inspect the known code seam and existing repository rules. Check `openspec --version` at workflow start; it must equal 1.12.0. On any version mismatch, stop and escalate to the parent before running the workflow; do not silently upgrade, downgrade or continue on an untested contract. If absent, ask the parent to install via `bash "$HOME/.megai/lib/install_openspec.sh"`; children never install tools. Keep `OPENSPEC_TELEMETRY=0` for CLI calls.
2. Work in the authorized task worktree. If the repository has no OpenSpec root, initialize only this repository with `openspec init --tools none --profile core --no-animation`. The single global Pi bridge is intentional: no generated OPSX prompt/skill bundle by default. Preserve any existing `openspec/config.yaml`, schemas, integrations and user artifacts; reconcile rather than overwrite.
3. Reuse the linked change. For a new one run `openspec new change <slug> --schema spec-driven --json`. Confirm the returned root/change path is inside the authorized checkout; external stores or unexpected roots require a parent decision.
4. Use `openspec status --change <slug> --json`, then `openspec instructions <artifact> --change <slug> --json` for the ready artifact. Read dependencies and relevant code only; keep `context`, rules, and returned paths distinct from generated content. Stop on failed/invalid JSON instead of treating it as empty guidance.
5. Keep proposal, spec deltas, design, and tasks proportionate. Include scope/non-goals, affected interfaces, preserved behavior, failure/edge-case scenarios, verification and rollback. Every acceptance requirement needs observable evidence. Make `tasks.md` the sole detailed checklist, with requirement/scenario references and intended tests.
6. Before implementation, resolve material user-owned behavior or scope decisions with the user. An explicit, unambiguous implementation request need not incur another approval round. Review the spec for contradictions; structural completeness is not acceptance.

## Implement and verify

The parent assigns each writer only the relevant scenarios, code paths, checklist items, validation and authority. One writer per checkout/worktree; parent serializes shared spec/checklist edits across parallel worktrees. Read-only children report findings without editing artifacts or installing tools.

Use `openspec instructions apply --change <slug> --json` for current context and task paths. Implement only authorized scope. Tick a task only after its stated evidence passes; skipped or failed checks remain explicit. Stop on spec/code disagreement and reconcile the contract rather than silently changing requirements to fit the code.

At handoff:

- Run `openspec validate <slug> --type change --strict --no-interactive` for structural spec validity.
- Run the task's actual regression tests and relevant diagnostics/build. Use independent review for risk or repository policy, not automatically for every artifact.
- Record requirement → code path → command/result → remaining gap in a compact `verification.md` beside `tasks.md`; reference existing test output instead of copying logs.
- `status.isComplete` means planning artifacts exist, not implementation success. `/opsx:verify` is advisory and archive can proceed with warnings; neither replaces passing tests or parent acceptance. Open critical findings block our handoff.

## Handoff, archive and stop

Finish required dev delivery through the existing worktree lifecycle. Keep Asana `In Review`, `completed=false`, and the `.todos` line unchecked with its change link. Only the user may mark Asana Done. The OpenSpec change remains active while awaiting user review; neither archive nor a checked checklist authorizes Asana Done or main promotion.

Archive only after explicit user approval of that change and passing verification. Before archiving, fetch current `instructions archive` and `instructions specs`; review the concrete delta paths and sync diff. Stop on errors, conflicts, unchecked tasks or missing evidence. Never use `--no-validate` or blanket force to bypass a gate. Archive is not a Git merge or a production release. Stop after the requested change.
