# MEGAI slim — Pi only

A dedicated, persistent **`slim`** distribution for **Pi coding agent only**. It keeps nine selected tools plus
bundled Caveman core, Plane-only task boundaries and task-quality gates. Installation and launch do not
merge or push Git branches. This branch is not automatically integrated into `main`.

## Included stack

| Tool | Purpose |
| --- | --- |
| [codedb](https://github.com/justrach/codedb) | Default core structural lookup via CLI; on-demand indexing |
| [zvec-grep](https://github.com/zvec-ai/zvec-grep) | Local hybrid code search; explicit indexing |
| [rtk](https://github.com/rtk-ai/rtk) | Default supported discovery output; raw acceptance diagnostics remain authoritative |
| [Caveman core](https://github.com/JuliusBrussee/caveman) | Default full terse chat; bundled MIT core adaptation, no companion/runtime package |
| task-flow | **Plane-only** identity, acceptance and start/handoff boundaries |
| [Ruff](https://docs.astral.sh/ruff/) | Non-mutating Python lint/format checks |
| [agent-memory](https://www.agent-memory.dev/) | Default relevant recall; lazy local service, saving only on user request |
| agent-worktree-lifecycle | Isolated writers and verified, user-agreed branch delivery |
| [ux-ui-agent-skills](https://github.com/plugin87/ux-ui-agent-skills) | Task-appropriate UI/UX and accessibility guidance |
| [Matt Pocock's skills](https://github.com/mattpocock/skills) | Engineering, diagnosis, specifications and verification workflows |

Native read/edit/bash, Git, `rg`, Plane connector configuration and Pi's lazy MCP
adapter are infrastructure, not additional product entries. Graphify,
RepoWise, Caveman companions/engines, ui-craft, Dembrandt, Argent, Numasec,
OpenSpec, legacy model routing and full Pi extension bundles are outside the active slim pipeline.
Historical standalone source remains unwired; old full-profile flags do not
restore it through slim install/update/launch.

## Install

Requires macOS/Linux, Python **3.11+**, Git, ripgrep and curl. The installer
resolves jq and Node **22+**; Ruff reuses an existing working executable or uses
uv/pipx. Authenticate your chosen harness separately. Credentials and model/
thinking choices are never installed or changed for performance.

```bash
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/slim/install.sh | bash
source ~/.zshrc  # or reopen your shell
megai status
megai doctor
megai pi        # Pi is the only supported harness
```

The installer itself defaults to `MEGAI_REF=slim`, so that command cannot silently
fetch `main`. It does **not** apply this repository's changes to your current host
until you explicitly run it. Existing valid tools are reused, including during
`megai update`; updates refresh slim source wiring/skill kits, not unrelated tools.

Fresh downloads pin agent-memory 0.9.27, zvec-grep 0.2.1, RTK 0.43.0 and both skill
kit source commits. Codedb fresh installs pin 0.2.56 with embedded SHA-256 hashes
for macOS ARM64/Linux x86_64; other platforms require a pre-provisioned trusted
CLI. No upstream codedb installer, hooks, extra services or MCP registrations run.
Existing codedb MCP settings remain user-owned. RTK's pinned installer is SHA-256 checked and verifies its
release archive; slim never runs `rtk init -g`. Npm core CLI installs disable
lifecycle scripts. Reused executable versions and platform dependencies may vary;
offline integration tests do not prove every fresh upstream install works.

## Plane-only workflow

Configure the secure connector explicitly; no credentials are bundled:

```bash
megai plane bridge install
megai plane setup --workspace SLUG --token-file /private/path/to/plane-token --client pi
megai plane status --client pi
```

The parent loads `megai-task-flow` once before project changes. Reuse known UUIDs;
otherwise consume all project/work-item/state pages and require unambiguous
matches. After a successful complete lookup finds no matching task, create exactly
one automatically in `In Progress`, without asking. Ambiguity or an unavailable
Plane boundary blocks edits rather than creating duplicates or a local fallback.

- Start once in started **In Progress**.
- Keep acceptance and execution evidence in the same Plane item.
- Verify task behavior and agreed branch delivery; hand off in started **In Review**.
- Only the user marks **Done** or approves main promotion.

There is no `.todos` creation, reading, writing, mirroring, ADLC board, monitoring,
board hook, routine milestone sync or queue draining in the active slim workflow.
Historical project boards stay untouched. Pure questions/read-only investigation
need no tracked mutation; refinements reuse the active item.

## Default behavior and acceptance

All ten stack entries are installed/wired by default for Pi.
Pi itself must be installed and authenticated separately. Their triggers are:

- **Caveman:** load the bundled core once; full terse chat in the user's language.
  `normal mode`/`stop caveman` opts out. Artifacts, uncertainty and warnings stay clear.
- **codedb:** first choice for relevant structural lookup; existing indexes are reused.
- **zvec-grep:** first choice for unknown wording/intent; CLI plus lazy Pi MCP.
- **RTK:** default agent policy for supported discovery commands such as
  `rtk git status`, `rtk git log -5`, and `rtk ls`. This is not a shell-wide or
  tool-call rewrite hook; compound commands and scripts remain native.
- **task-flow:** start/reuse the Plane task before project edits; hand off only
  after verified acceptance in In Review, never Done.
- **Ruff:** non-mutating checks for changed Python files.
- **agent-memory:** when prior decisions matter, start the local service and
  recall relevant context without a separate enablement request. Saving still
  requires the user's persistence request; no secret or personal-data ingestion.
- **agent-worktree-lifecycle:** isolated writes and verified agreed branch delivery.
- **UX/UI kit:** select the matching UI/accessibility skill for UI work.
- **Matt Pocock kit:** select the matching engineering/diagnosis/verification skill.

Defaults are task-appropriate choices, not ten compulsory calls per task. Before
edits define the observable outcome, acceptance checks and stop condition. Run
repository tests/build/lint unchanged with raw output and original exit status;
review full native diffs. RTK summaries alone never prove acceptance. Keep security,
accessibility, compatibility and independent-review gates. User resource exclusions
and model/provider/thinking choices remain untouched. If an exclusion disables a
default, report that instead of claiming the tool is active.

No daemon or model call is added to harness startup. Start memory only for a
relevant recall; index only when a task needs it;
missing/stale indexes must be reported rather than silently treated as results.
Smaller context/output is not a measured speed or quality improvement.

## On-demand operation

```bash
megai start agent-memory
megai-memory recall "relevant decision"
megai-memory save "decision to persist"  # only when persistence is requested
megai-codedb index .                    # codedb indexing only when needed
megai-codedb symbol MySymbol            # default structural lookup
megai reindex                           # initializes/rebuilds zvec explicitly
zg query "where authentication is validated"
rg -n 'exact_symbol' src/
megai stop agent-memory
```

MEGAI's preparation before Pi launch performs only local wiring/worktree checks:
no daemon startup, index building, provider requests, model selection or legacy
routing overlay. Pi itself retains its own network/resource behavior. Existing index configuration is retained on rebuild; configure any
remote embedding separately only after explicit authorization. Missing or stale
wiring fails with a repair instruction rather than silently launching a broken
stack.

Skill descriptions are discovered by the harness; full bodies are loaded only
for matching tasks. Existing user skill/package filters are preserved. Use
`pi config` to select resources rather than forcing every specialist into startup.
Preserve acceptance tests, accessibility, compatibility, error handling and
independent security/data-integrity review. Use raw diagnostics when compressed
output could conceal evidence. Fewer tools/jobs alone are **not** proof of faster
completion, lower token costs or equal model quality.

## Adoption, preservation and rollback

**Migrating an existing full installation is deliberately fail-closed.** A
read-only preflight runs before replacing distribution source or running package
installers. Legacy board/routing instructions, conflicting skills/proxies,
malformed configs (including shell PATH blocks) and symlinked destinations require manual reconciliation;
slim does not guess ownership or delete custom registrations by name. Existing
unrelated hooks, MCP tables, auth, models and package selections remain unchanged.
It also does not stop already-running services or override user-owned extensions.
A preserved custom extension can still have its own startup behavior.

The installer, update, doctor, wire, Plane setup/remove/restore and uninstall
operate only on Pi. `megai cc`, `megai codex`, `megai omp`, non-Pi wire targets and
Plane `--client all|codex` are rejected before mutation. Historical non-Pi source
and recovery artifacts are not active entrypoints.

Skills are installed only under `~/.pi/agent/skills` (or `PI_CODING_AGENT_DIR`).
Skill-kit sources live under `~/.megai/pi-kits/`; old shared kit trees and other
harness registrations are preserved. Pi defaults exclude automatic
`~/.agents/skills/**` discovery to avoid inheriting old shared copies; existing
explicit Pi resource selections follow this default and remain authoritative.
Previously installed Claude/Codex/OMP policies are not removed or rewritten.

Try alongside a full installation in a separate user/container environment.
Changing `MEGAI_HOME` alone does not isolate Pi's global configuration.
For adoption on an existing host, back up and manually detach the specific legacy
registrations reported by preflight, review user resource filters, then retry.
Do not delete project boards or indexes to resolve a wiring conflict.

Successful wiring records exact ownership hashes and private recovery manifests
under `~/.megai/backups/slim-wiring-*/`. Source replacements and skill-kit updates
retain prior bytes/trees in backups. On a wiring write failure, already-applied
changes roll back; failures in a third-party tool installer are reported and are
not represented as an atomic all-tools rollback. Re-run after resolving the failure.

```bash
megai update
megai wire pi
megai uninstall  # detaches owned slim wiring/Plane connector; tools and data remain
```

For rollback, reconcile later edits first, then restore only each manifest's
listed target from its numbered backup. A `null` manifest value means the target
was newly created. Restore previous skill-source trees separately if needed.
Uninstall preflights owned skills, policies and shell PATH blocks before changing
Plane. If a later write fails, recovery manifests and connector restore backups
remain available. It never recursively deletes MEGAI, skill kits, credentials,
indexes or historical project data. Main promotion remains a separate decision.

## Verification

```bash
bash tests/slim-distribution.sh  # isolated offline install/update/wiring/runtime contracts
bash tests/pi-performance.sh    # adapter selection and user-package preservation
bash tests/agent-memory-port.sh
bash tests/ruff-integration.sh
bash tests/ux-ui-agent-skills.sh
bash tests/orchestration-policy.sh
```

The slim contracts use disposable outer HOME/config roots and fake backends;
they make no model calls or live app requests. They verify branch selection,
exact installer dispatch, idempotence, conflict refusal, preservation, on-demand
startup, CLI behavior and quality-policy clauses—not a performance benchmark.
