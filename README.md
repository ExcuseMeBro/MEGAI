# 🚀 MEGAI · Pi defaults

The `pi` branch provides a clean global Pi setup. Configuration lives in
`~/.pi/agent`; local project exceptions live in each project's `AGENTS.md` and
`.pi/project.json`. The installer does not create backups. It requires Python 3.11+, Node 22.22+,
Git, npm, uv and jq, and uses the standard home directories (custom
`MEGAI_HOME` / `PI_CODING_AGENT_DIR` values are rejected).

## ⚡ Quick start

> ⚠️ **Reset is destructive:** Pi credentials, sessions and old settings are deleted without a backup.

```bash
# From this branch's checkout. --reset deletes Pi auth, sessions and old settings.
python3 pi-defaults/install.py --reset --remove-omp
# Open Pi, then use /login to authenticate the freshly reset agent.
pi
megai doctor
```

For a remote installation, download and inspect this branch's `install.sh`, then
run it with `MEGAI_REF=pi MEGAI_PI_RESET=1 MEGAI_REMOVE_OMP=1`. Reset/removal are
explicit options. Reinstallation of a clean profile reuses its pinned packages;
Pi startup never updates packages or builds indexes automatically.

## 🧰 Included tools

| Default | Purpose |
| --- | --- |
| 🤖 Pi 0.85.1 | Native agent, user-selected provider/model |
| 🐍 Ruff | Check changed Python without automatic fixes |
| 🧠 Headroom 0.37.0 | Local discovery compression; raw source/tests/failures |
| 🔎 codedb / tgrep 1.0.4 / zvec-grep 0.2.1 | Structure, ranked text, local intent search |
| 🔌 pi-mcp-adapter 2.33.0 | Lazy Plane and zvec MCP |
| 🌐 pi-web-access 0.29.0 | Exa public search without a separate key, page fetching |
| 🌳 Native Git worktrees | Verified task isolation; parent self-reviews |

Package versions and integrity hashes are in [package-lock.json](pi-defaults/package-lock.json).
Native Git worktrees isolate task writers; no external workspace manager is required. Shared legacy skill discovery
is excluded from this Pi profile to avoid contradictory defaults. Other agents retain
their own configuration.

Model routing stays user-selected: the repo ships separate explicit opt-in `native`
and `economy` presets. `native` uses GPT Sol coordination, a DeepSeek Flash high
worker and GPT Astra review; `economy` keeps its distinct DeepSeek role mix. Nothing
is applied until you run a preset command yourself. Measure a change instead of assuming it: `megai report --text`
reports turns, prompt tokens per turn, reported cost per model and estimated
tool-output replay from local sessions, and `megai budget --check` previews the
optional native context budget without writing.

<a id="token-economy"></a>

## 🪙 Token economy

Prompt size multiplied by turn count is the whole bill: `cacheRead` is about 96% of
reported tokens in the observed local window. Four habits cover it.

**1. Inspect a command yourself with `!!`.** `!command` runs a shell command and sends
its output to the model; `!!command` runs it without adding the output to context. Use
`!!` for anything you read yourself — versions, git status, `ls`, logs — and ask the
agent for the one line you actually need. The agent is also told to reuse what you
already inspected instead of reproducing the same output.

**2. Keep long-term rules in `AGENTS.md`, procedures in skills.** `AGENTS.md` is sent
with every request, so its size is charged on every turn; a skill is loaded only when
its trigger fires. Measured on this repository (chars/4, an estimate):

| File | Before | After |
| --- | --- | --- |
| `pi-defaults/AGENTS.md` (every request) | 17,862 chars ≈ 4.4k tokens | 16,410 chars ≈ 4.1k tokens |
| `pi-skill/delegation.md` (only when delegating or escalating) | 12,197 chars | 15,147 chars |

The blocked Codex Spark procedure and the parent-side provider-timeout/replacement
sequence moved out of `AGENTS.md` into `pi-skill/delegation.md`. Sections that are used
on almost every task (discovery, placement, context budget) stay in `AGENTS.md`:
moving them to a skill would load them anyway and only add a lookup step.

**3. Enable tools by task.** Built-in tools come from `defaultTools` in
`~/.pi/agent/settings.json` (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`), and
a project `.pi/settings.json` replaces it, so a repository can run narrower than your
global default. For a one-off narrow session, allowlist tools at launch:

```bash
pi --tools read,grep,find,ls -p "Review this file"   # strict allowlist: built-in,
                                                     # extension and custom tools
pi --exclude-tools web_search,fetch_content         # filter the resulting list
pi --no-builtin-tools                               # extension tools only
```

MCP servers in `~/.pi/agent/mcp.json` already declare `lifecycle: lazy`, so an unused
server is not connected at startup. `defaultTools` selects **built-in** tools only;
extension and MCP tools stay enabled, so narrow them with `--exclude-tools` when it
matters.

**4. Break long work into phases.** `/compact` summarizes older turns while keeping
recent work, and a new task belongs in a new session. Compaction is itself a
summarization request that can omit detail: in the observed 14-day window it ran 5
times for a reported $4.46, against 4,326 turns. Compact at phase boundaries, not per
message, and do not re-read logs a finished phase has already discarded.

Measure the whole picture with `megai report --text`. Reported cost is
provider-reported, not billed, and every token figure here is an estimate from local
sessions, not a benchmark. For the handoff question specifically — how much work an
agent repeats after another agent already read it — use
`benchmark/handoff-cost/measure.py`.

<a id="plane-and-branches"></a>

## 🗂️ Plane and branches

Workspace `brodev`: **Todo → In Progress → In Review → Done**. Plane is the only
execution tracker. Technical designs and verification receipts are artifacts,
not a second board. The existing private Plane token stays outside Pi and Git at
`~/.config/megai/credentials/plane-api-token` (mode 600).

```bash
pi-workflow context
pi-workflow start --title "Exact task title"
pi-workflow review --project-id UUID --task-id UUID \
  --receipt delivery.json --evidence-file verification.txt
# After explicitly approved main promotion in every affected repository:
pi-workflow done --project-id UUID --task-id UUID
```

The review receipt lists **all affected repositories**, their delivered commit SHAs
and remotes. `review` binds it to the Plane task and canonical project, stores primary
checkout paths, pins remote URLs, and preserves previous delivery coverage.
`done` fetches each remote main and checks commit ancestry before changing Plane.
A missing merge or changed item leaves the task In Review. Plane lacks conditional
updates: serialize task boundary edits; the command checks for concurrent changes
immediately before its final write. There is no unattended watcher or automatic merge.

The global `/factory all` prompt implements the current Plane project's Todo and
In Progress tasks sequentially, refreshing after each verified In Review handoff
until a complete lookup finds neither state remaining. `/factory 12,34,56` limits
the run to those task numbers; qualified project IDs and UUIDs are also accepted.
No `factory-ready` label is needed. Bare `/factory` shows usage without starting work.
`pi-workflow factory-plan --selection all` performs read-only queue discovery;
`factory-start` starts/resumes only the selected existing UUID. Independent tasks
continue past task-local blockers; a queue with only blockers stops honestly with
remaining IDs, without pretending it is empty. Existing worktree, tests/review,
local dev delivery and approval rules apply; no push, main promotion or Done.
Run `/reload` in an existing Pi session after installation. This is an agent prompt,
not an unattended daemon, distributed lock or enforcement boundary.

The `/mdev` and `/prdev` prompt templates are installed globally: `/mdev` is explicit
authorization to reconcile, review, merge and push task work into `dev` (no repeated approval)
and to clean safe local task workspaces. `/prdev` authorizes a necessary verified non-force
dev push and opens or reuses the `dev` → `main` pull request without merging. Neither promotes
`main`; both bind evidence to exact SHAs and reserve shared publication targets through
`megai queue`. Existing PRs are revalidated by repository and branch identity, not duplicated
when their heads move. An already-integrated dev head is a completed no-op.

Both complete recoverable prerequisites instead of stopping: a local `dev` ahead of its remote,
ignored or ignored-untracked files, a missing Plane identity, missing or stale evidence, a moved
ref and an ordinary `dev`-vs-`main` difference are work to finish. Failed verification,
unavailable evidence/authentication, ambiguous ownership/destinations, exhausted bounded recovery
or actions outside authorization hold the affected row; independent rows still proceed.
Uncommitted task work remains explicitly unfinished even if its pinned commits were delivered.
Ignored files
never block that decision, but the `dev` fast-forward uses `--no-overwrite-ignore` so a
colliding ignored file is preserved and reported instead of silently overwritten.

The credentials-free [saved local Pi profile](pi-defaults/local-profile/README.md) records
the current model, thinking, timeout, fallback and MCP preferences. It is an explicit
restoration reference; installing MEGAI does not silently replace preferences with it.

The persistent branches are `dev` and `main`. Normal task branches start from dev
in verified task-owned Git worktrees and deliver to dev after tests/review. Main promotion
requires explicit approval. A specifically requested persistent branch overrides
dev delivery: push only that branch, retain its worktree, leave the task In Review
until it reaches main. A persistent branch such as `pi` is used only when the task or
the user explicitly requests it.

A monorepo gets one worktree per task. A folder containing separate repositories
gets one worktree per affected repository under the same existing Plane task. The coordination folder remains a non-Git folder. The project-rules
extension loads original project rules even when worktrees live outside that folder.

<a id="local-project-configuration"></a>

## ⚙️ Local project configuration

Copy [the template](pi-defaults/projects/template.json) to `.pi/project.json` in a
project. For grouped repositories use `layout: "multi"` and component-relative
paths in `repositories`. Set `planeProject` to an existing exact Plane project name;
the setup never creates missing Plane projects. Preserve repository-specific rules.

[ADAM's template](pi-defaults/projects/ADAM.json) and [local policy](pi-defaults/projects/ADAM.md)
keep Forgejo at `git.adam.uz`, one ADAM Plane project, and persistent `validationsdk`
branches in `mobile` and `main-be`. The global installer does not edit project files
or create/delete project branches. Existing dirty work and branch protections are
retained. Read `pi-workflow` for worktree creation and branch cleanup rules.

<a id="verification-and-operation"></a>

## ✅ Verification and operation

```bash
python3 -B tests/pi_defaults.py
python3 -B tests/pi_context_budget.py
python3 -B tests/pi_usage_report.py
python3 -B tests/handoff-cost.py
python3 -B benchmark/handoff-cost/measure.py --days 14
ruff check --no-fix --no-fix-only --force-exclude --no-cache -- pi-defaults/*.py lib/pi_context_budget.py lib/pi_usage_report.py tests/pi_defaults.py benchmark/handoff-cost/measure.py tests/handoff-cost.py
bash -n bin/megai install.sh
node pi-defaults/verify.mjs  # installed Pi; no model request
megai doctor
```

A clean reset removes Pi login credentials too. `/login` is the required human step
before model requests; installation and loader/tool checks do not prove model auth.
Use `/reload` or reopen existing Pi sessions after configuration changes. Package
installation grants the extensions normal Pi process access. Public web searches
must not contain private repository content or credentials.

## 📚 Upstream references

[Pi packages](https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/packages.md),
[web access](https://github.com/nicobailon/pi-web-access),
[MCP adapter](https://github.com/nicobailon/pi-mcp-adapter).

### Focused engineering workflow

Pi ships four adapted Matt Pocock skills: `codebase-design` for interfaces,
`diagnosing-bugs` for reproductions, `tdd` for behavior changes, and `code-review`
for Standards and Spec checks. They load on demand; Plane and Pi workflow retain
tracking and delivery. Docs and small config changes use focused validation.
Ponytail, OpenSpec and the automatic Superpowers bootstrap are retired. Existing installations
can run `MEGAI_SOURCE=/path/to/MEGAI python3 /path/to/MEGAI/lib/pi_engineering.py --apply`
to migrate only engineering settings with private backups; custom skill collisions
stop before writes. Use `--verify` for installed-byte checks and native Pi loading
for activation (`node pi-defaults/verify.mjs --engineering-only` checks this scoped
workflow without requiring optional web tools). Restart Pi sessions after updating.

Historical specifications are preserved under `docs/history/specifications/`;
they are records, not an active OpenSpec workspace or execution tracker.
