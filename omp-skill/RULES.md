<!-- megai:paseo-placement:begin -->
# OMP smart routing and Paseo placement

## Smart code discovery

- Use direct LSP, index, search, and exact reads first. Invoke MiniMax `smart-router` only for read-only search/read/find, symbols, references, callers, and existing-pattern evidence.
- One empty/conflicting MiniMax lookup may escalate once to Luna or Terra. MiniMax never edits files, writes tests, reviews code, runs migrations, or owns a task worktree.
- New settings apply to new sessions/task resolutions. If a writer resolves to any MiniMax model, stop it and relaunch once on `gpt-core-worker` or `gpt-fast-worker`.

## Worker model routing

- OMP is the single model gateway. GPT owns every code write: Terra medium for core logic, GPT-5.4 Mini for small edits/tests, GPT-5.5 for migrations/debugging, GPT-5.4 for compatibility, and Spark for tiny mechanical changes.
- MiniMax Code M2.1 Lightning is read-only discovery infrastructure. Never route implementation, tests, refactors, migrations, Docker changes, commit writing, code review, or fallback writes to MiniMax.
- Generate commit messages directly in the parent; never add a model call solely for commit text. Git lifecycle remains deterministic.
- Do not chase a fixed provider ratio. Enforce GPT write authority and MiniMax read-only authority. No free OpenCode models or duplicate MiniMax-in-Pi routing.

## Bounded execution

- Run MiniMax-assisted discovery only when needed, then GPT implement → GPT code self-review → GPT focused tests → `megai finish --verified --target dev` when delivery is required.
- UI checks are code-only by default: component structure, state handling, accessibility semantics, token/style consistency, diagnostics, and focused component tests. Browser, simulator, screenshot, visual, design, and accessibility-audit loops require an explicit user request.
- Do not run automatic planner/reviewer/final-gate agents, TDD loops, integrated full suites, queue draining, or `/loop`. One focused failure may escalate once to one specialist.
- After dev delivery and task completion, ask whether to promote main. Run `megai promote --approved` only after an explicit affirmative reply; otherwise leave main unchanged.

## Paseo agent placement

- The orchestrator stays in the primary `dev` workspace.
- In an agent-scoped Paseo session, read-only discovery, planning, and review workers use `create_agent` without `workspaceId`, so they appear as tabs in the orchestrator workspace.
- In a top-level context, require exactly one workspace whose `cwd` equals the current `cwd`, then pass its ID to `create_agent` for read-only workers; ask once on zero or multiple matches.
- Every write-capable worker MUST be `gpt-core-worker`, `gpt-fast-worker`, or an explicit GPT specialist in a managed worktree from `dev`.
- Never create a MiniMax writer, concurrent writers in the parent workspace, or a bare writer agent. Shared-file/schema/migration boundaries are serialized through one GPT writer.
- Cross-workspace workers remain attached to the parent Subagents track. After verified dev merge/push, one open promotion request, and worktree cleanup, call `archive_workspace` for that worker workspace. Never archive primary `dev`, dirty, failed, conflicted, or unmerged work.
- Outside Paseo, OMP native task isolation may provide ephemeral worktree/branch isolation; inside Paseo, visible writer workspaces take precedence.
<!-- megai:paseo-placement:end -->
