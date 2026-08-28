---
name: smart-development-orchestrator
description: Route development across OMP MiniMax Code M3 and GPT-5.6 roles with token-aware complexity escalation, parallel worktrees, and safe dev integration.
managed-by: megai
---

# Smart Development Orchestrator

One parent owns decomposition, routing, contracts, integration, and final acceptance. Workers never decide global scope or integrate their own branches.

## Placement

- Keep the orchestrator as the top-level agent tab in the primary clean `dev` workspace.
- Keep read-only discovery, planning, and review workers as subagent tabs in that same workspace.
- Give every concurrent writing slice its own Paseo-managed worktree workspace and task branch from the same `dev` baseline.
- Assign one writer per non-overlapping file set. Serialize shared files, schemas, migrations, and dependency-ordered boundaries.
- Cross-workspace workers remain attached to the orchestrator's Subagents track. Never detach them automatically.

## Discovery routing

- Exact file, symbol, reference, caller, test, config, and routine repository exploration: OMP MiniMax Code M3 at low effort.
- If the first focused MiniMax lookup is empty, conflicting, or requires a trusted reading path, use one GPT-5.6 Luna scout.
- Cross-module architecture, data flow, impact, or hard-debugging exploration: GPT-5.6 Terra or Sol.
- Use LSP/symbol/index search before broad reads. Batch independent lookups, return compact `path:line` evidence, and never repeat resolved ranges.

## Provider routing

OMP is the single model gateway. Do not duplicate MiniMax configuration in Pi and do not route work to free OpenCode models.

Use `minimax-code/MiniMax-M3` for routine exploration, implementation, CRUD/API work, tests, Docker, ordinary migrations, and routine refactors. The provider is unavailable while `MINIMAX_CODE_API_KEY` is absent. The key must be rotated if disclosed and stored outside source; do not paste it into prompts, config, logs, or task contracts.

Use GPT-5.6 through OMP for planning, architecture, hard debugging, critical review, payment/auth/security, destructive or production configuration, complex refactors, and final integrated acceptance. A trusted parent classifies the task before dispatch. Before sending private code to MiniMax, require operator approval covering MiniMax terms, logging/retention, key storage, data residency, model quality, and fallback behavior.

## Complexity routing

- **LOW:** MiniMax exploration → MiniMax implementation/test → focused verification → done. GPT review only on a concrete risk trigger.
- **MEDIUM:** MiniMax implementation → Terra review when the diff changes a contract, crosses modules, fails once, or is selected by quality sampling.
- **HIGH:** Sol/Terra plan → MiniMax bounded implementation workers → mandatory GPT final review.
- **CRITICAL:** Sol plan → GPT owns sensitive core implementation; MiniMax may handle only isolated non-sensitive mechanical slices → Sol review/fix.

Treat 60% MiniMax / 40% GPT as a non-binding observed-token target, not a routing gate. Report the measured provider share when reliable telemetry is available, but change routing only from task complexity, defect/retry evidence, or explicit operator policy. Never reduce a required review to chase the ratio.

## High-speed ADLC

- **Spec + risk:** MiniMax handles LOW/MEDIUM; Sol handles HIGH/CRITICAL and protected boundaries.
- **Discovery:** MiniMax returns compact evidence in at most two focused tool waves; Luna is the trusted fallback.
- **Plan:** MiniMax produces routine contracts; Terra/Sol produces architecture and critical contracts.
- **Generate:** up to four `minimax-worker` agents implement independent bounded slices in parallel worktrees; each runs focused tests and commits.
- **Verify + review:** workers verify locally; Terra reviews sampled MEDIUM and every HIGH diff; Sol owns CRITICAL and final integrated acceptance.
- **Ship:** integrate verified commits into `dev`, run the integrated suite once, push `dev`, open/reuse the `dev` → `main` PR/MR, then archive only successfully merged worker workspaces.

Do not run a separate model/tool round trip for every ADLC label. Do not run the full suite in each worker. One failed MiniMax diagnosis escalates to Terra; repeated failure routes implementation to GPT.

## Fanout

1. Resolve the target Git repository and observable acceptance conditions.
2. Confirm clean `dev`, `main`, and `origin`; use `megai dev` only from a clean primary `main`/`master` checkout.
3. Define shared interfaces and non-overlapping file ownership before spawning.
4. Launch all genuinely independent slices concurrently, capped at six agents. Reuse suitable live agents instead of duplicating them.
5. Give each child: goal, repository/cwd, scope, authority boundary, evidence, acceptance, validation, compact output, and stop rules.
6. Require each writer to commit a clean, focused task branch after verification.
7. Integrate successful branches into `dev`, then verify the integrated tree once.
8. Run `megai finish --verified --target dev` to push `dev`, open or reuse the `dev` → `main` PR/MR, and clean only successfully merged registered worktrees/branches.
9. After the dev push, PR/MR, and worktree cleanup succeed, call Paseo `archive_workspace` for each successfully merged worker workspace. Never archive the orchestrator/primary `dev` workspace or any dirty, unmerged, failed, or ambiguous workspace.
10. Never auto-merge `main`; human review or protected CI merges the PR/MR.

Stop on dirty or ambiguous ownership, missing branches/origin, failed verification, conflicts, provider/auth failures, or failed push/PR creation. Keep external work incomplete until the PR/MR and required cleanup succeed.