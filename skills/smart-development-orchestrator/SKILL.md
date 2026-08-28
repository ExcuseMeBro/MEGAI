---
name: smart-development-orchestrator
description: Route development across Luna, Terra, trusted coding models, and approved free OpenCode models; coordinate parallel agents with safe Paseo workspace and dev-branch integration rules.
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

- Exact file, symbol, reference, caller, test, config, or narrow-range lookup: OMP GPT-5.6 Luna at low effort.
- Cross-module architecture, data flow, impact, conflicting conventions, or an unresolved Luna lookup: one read-only OMP GPT-5.6 Terra worker at medium effort.
- Use LSP/symbol/index search before broad reads. Batch independent lookups and return compact `path:line` evidence.
- The parent does not repeat resolved reads; it reads only an exact edit or verification range.

## Provider routing

Default to trusted OMP, Codex, or Claude agents. They are mandatory for private/proprietary code, credentials, personal data, auth/security, schemas, migrations, irreversible changes, integration, and final review.

Free OpenCode dispatch is default-deny. Before every free-provider task, require both: (1) explicit classification of the exact payload as public code or a synthetic fixture, and (2) an operator-approved provider privacy attestation covering every upstream provider, terms, logging/retention, key storage, data residency, model quality, and fallback behavior. Missing either gate routes the task to a trusted provider.

After those gates pass, use:

| Model | Use |
| --- | --- |
| `opencode/nemotron-3.5-lightning-free` | Tiny mechanical edits and data collection |
| `opencode/muse-spark-1.2-contributor-free` | Large-context public implementation |
| `opencode/nemotron-3-ultra-free` | Public repo-wide read-only analysis |
| `opencode/hy3-free` | Public architecture second opinion |
| `opencode/mimo-v2.5-free` | General public-code fallback |

Never send secrets, credentials, personal data, private code, or unclassified context to a free provider. A trusted model must review every free-provider change before integration.

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