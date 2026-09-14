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
| 🦸 Superpowers 5.1.0 | Automatic bootstrap and matching engineering skills |
| 🐴 Ponytail 4.9.0 | Default full mode; smallest complete implementation |
| 📐 OpenSpec 1.13.0 | Global core skills and `/opsx-*` commands, telemetry disabled |
| 🔌 pi-mcp-adapter 2.33.0 | Lazy Plane and zvec MCP |
| 🌐 pi-web-access 0.29.0 | Exa public search without a separate key, page fetching |
| 👥 pi-subagents 0.67.0 | Bounded children inheriting the selected model |

Package versions and integrity hashes are in [package-lock.json](pi-defaults/package-lock.json).
Superpowers' extra `dispatch_agent` extension is excluded because pi-subagents owns
delegation. Shared legacy skill discovery is excluded from this Pi profile to avoid
contradictory defaults. Other agents retain their own configuration.

<a id="plane-and-branches"></a>

## 🗂️ Plane and branches

Workspace `brodev`: **Todo → In Progress → In Review → Done**. Plane is the only
execution tracker. OpenSpec specifications and verification receipts are artifacts,
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

The persistent branches are `dev` and `main`. Normal task branches start from dev
in managed Paseo worktrees and deliver to dev after tests/review. Main promotion
requires explicit approval. A specifically requested persistent branch overrides
dev delivery: push only that branch, retain its worktree, leave the task In Review
until it reaches main. `pi` is this task's explicitly requested delivery branch.

A monorepo gets one worktree per task. A folder containing separate repositories
gets one worktree per affected repository under the same existing Paseo project and
Plane task. The coordination folder remains a non-Git folder. The project-rules
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
ruff check --no-fix --no-fix-only --force-exclude --no-cache -- pi-defaults/*.py tests/pi_defaults.py
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
[Superpowers](https://github.com/weiping/pi-superpowers),
[Ponytail](https://github.com/DietrichGebert/ponytail),
[OpenSpec](https://github.com/Fission-AI/OpenSpec),
[web access](https://github.com/nicobailon/pi-web-access),
[subagents](https://github.com/nicobailon/pi-subagents),
[MCP adapter](https://github.com/nicobailon/pi-mcp-adapter).
