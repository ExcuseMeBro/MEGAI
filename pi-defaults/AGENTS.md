# Pi defaults

Use the user's language. Keep the selected provider, model and thinking level.
Read the nearest project AGENTS.md and `.pi/project.json`; project-specific rules
stay there. In a worktree, `pi-workflow context` resolves the original repository
and lists the original project's rules too. Explicit user instructions take precedence.

Before project changes, load `pi-workflow`. Plane in workspace `brodev` is the
only execution tracker: Todo → In Progress → In Review → Done. Reuse the same
project/task identity. Done requires verified main delivery for every affected
repository; use `pi-workflow done`. Main promotion still needs explicit approval.
Questions and read-only investigation do not need a task.

For coding, use Superpowers' matching workflow and Ponytail's smallest complete
solution. Superpowers' plan/spec files are technical artifacts; its TodoWrite and
local checklist instructions map to the existing Plane item, not a second tracker.
The Pi workflow owns task identity, worktree placement and branch delivery when a
packaged skill suggests a different convention. Use OpenSpec for specifications
and substantial behavior changes; preserve existing specs. Initialize missing
project OpenSpec storage only when needed, with `openspec init --tools none`.
OpenSpec core skills and `/opsx-*` commands are installed globally. Its planning-only
boundary applies to planning requests; an explicit implementation request authorizes
continuing through apply after the necessary specification work.

Use codedb for definitions/outlines, tgrep for ranked text discovery, and zvec-grep
(`zg` or its MCP tools) for intent search. Use rg for exact/exhaustive matching and
native read for source verification. Index only on task demand; keep embeddings
local. Headroom automatically compresses eligible successful discovery output;
source reads, edits, full diffs, tests and failures remain raw. Never infer test
success from compressed output. Run Ruff on changed Python by default:
`ruff check --no-fix --no-fix-only --force-exclude --no-cache -- FILES`.
Use repository formatting rules; do not automatically rewrite unrelated files.

Use pi-web-access for public research. Keep private repository text and credentials
out of public search queries. pi-mcp-adapter provides lazy Plane and zvec tools.
Use pi-subagents for bounded independent tasks or required independent review;
otherwise work directly. Give children explicit cwd, scope and acceptance. Children
are leaves and never mutate Plane or integrate branches. One writer per worktree.
Use completion notifications. Security/data-integrity or consequential cross-module
changes require a fresh independent reviewer. Verify behavior before handoff.
