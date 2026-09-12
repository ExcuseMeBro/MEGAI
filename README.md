# MEGAI

MEGAI is a harness-neutral coding workflow for **Pi, Claude Code (cc), Codex and
OMP**. It keeps the selected provider, model, thinking level, credentials, native
arguments and user-owned resources unchanged. This branch is prepared for parent
review; it does not promote itself to `main`.

## Capy adaptation

The persistent `capy` branch contains an experimental, manually supplied
[Capy instructions pack](capy/README.md). It does not add a Capy launcher or
installer, and does not imply native Pi-extension compatibility.

## Install

The public installer defaults to the integrated distribution and preserves an
explicit ref:

```bash
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | bash
# Optional deliberate branch/ref selection:
curl -fsSL https://raw.githubusercontent.com/ExcuseMeBro/MEGAI/main/install.sh | MEGAI_REF=dev bash
source ~/.zshrc  # or reopen the shell
megai status
megai doctor
```

Supported launchers forward native arguments unchanged:

```bash
megai pi [pi args]
megai cc [claude args]
megai codex [codex args]
megai omp --profile work [omp args]
```

`megai omp --profile work` preserves both the profile and all other OMP arguments.
The launcher performs local wiring/worktree checks only; it makes no provider
request, model selection, Plane mutation or startup daemon call.

## Active stack

| Tool | Purpose |
| --- | --- |
| Headroom 0.37.0 | Local discovery compression and explicit semantic memory |
| tgrep / codedb / zvec-grep | Text, structural and intent discovery |
| [Ruff](https://docs.astral.sh/ruff/) | Non-mutating Python verification |

- Headroom 0.37.0 in a pinned, hash-locked Python 3.14 runtime for local
  discovery compression and local ONNX semantic memory.
- tgrep, codedb and zvec-grep for task-appropriate discovery, structure and intent.
- Plane-only task-flow, worktree lifecycle, and task-appropriate skill kits.
- [Ruff](https://docs.astral.sh/ruff/) for non-mutating Python checks.
- Native harness configurations remain the source of provider/auth/model/thinking
  choices. RTK, Caveman and agent-memory are retired from the active defaults.

## Pi provider stall protection

Pi installs `megai-provider-guard`: a **180-second wall-time budget for a model
request and its automatic retries**, not a task deadline. It aborts the provider
wait with native Pi cancellation, preserves session/tool results, and records a
metadata-only `megai-provider-timeout` entry. Successful responses disarm it;
tool execution is never timed out by this extension, including nested model work
inside a tool. No provider, model, thinking, credentials or retry settings change.

`MEGAI_PROVIDER_TIMEOUT_MS` selects a different budget; `0` explicitly opts out.
Existing extension filters still win. Reload/reopen Pi after installation;
already-running processes do not acquire new extensions automatically. Do not
restart a writer mid-mutation. This bounds waiting rather than making providers
faster; after a timeout, reconcile saved evidence before resuming/escalating.

Native `retry.provider.timeoutMs` alone is insufficient for this incident: the
installed Codex SSE implementation times out headers, not the full response body.
See `docs/audits/pi-provider-stalls.md` for evidence and offline verification.

## Headroom use and compatibility

Pi has an automatic native extension. It compresses only eligible successful
read-only discovery output; native session messages, source reads, edits, tests,
full diffs and failures remain raw. `headroom_retrieve` pages exact originals,
which are repository-scoped and retained for seven days within a bounded cache.
`headroom_memory` provides explicit local recall/save; saves are only for requested
persistence. `MEGAI_HEADROOM=0` disables Pi automation and normal mode or
`/headroom-verbosity 0` disables concise guidance.

Claude Code, Codex and OMP do **not** receive invented interception hooks,
provider rewrites or API proxies. They use the same local bridge explicitly:

```bash
megai headroom doctor
megai headroom compress < discovery.txt
megai headroom retrieve ID
megai headroom recall "relevant prior decision"
megai headroom save "decision to persist"
printf '%s' '{"action":"compress","text":"..."}' | megai-headroom json
```

This is compatibility, not native-auto parity. Runtime assets are prepared during
installation and runtime network access is disabled. If Headroom is unavailable,
the Pi extension reports raw-context fallback and the other hosts report the CLI
failure; no silent active claim is made.

## Plane task labels

The parent applies the [task-label policy](task-flow/skills/megai-task-flow/SKILL.md#task-labels)
at task start/resume: one primary type (`bug`, `feature`, `refactor`, `docs`, `test`,
`chore`, `research`) and all applicable areas (`backend`, `frontend`, `mobile`,
`desktop`, `infra`, `data`, `design`, `tooling`). Optional concern labels require
explicit acceptance. Existing project mappings and custom labels are preserved;
missing labels are created on demand after complete lookup, then attached additively.
Ambiguity, missing permissions and uncertain writes block edits. This is agent
workflow policy, not API enforcement or retrospective relabeling of other tasks.
Pi wiring installs it without changing native model/auth settings; reload/reopen Pi
for refreshed skill discovery in existing sessions.

## Plane connector matrix

Plane remains the sole execution tracker. Configure only the clients you use:

```bash
megai plane bridge install
megai plane setup --workspace SLUG --token-file /private/path/to/token --client all
megai plane status --client all
# Supported client values: pi, codex, cc, omp, all
```

Pi uses its native `requestHeadersCommand` shape. Codex keeps its existing native
TOML integration. Claude Code uses `~/.claude.json` `mcpServers.plane`; OMP uses
`mcp.json` under its selected profile (`~/.omp/agent` or
`~/.omp/profiles/<profile>/agent`). CC/OMP use the receipt-verified local
`plane_mcp_remote.py` stdio bridge with a private token-file path and workspace
slug in configuration; the token itself is never placed in config or argv.

Every requested client is parsed and staged before the first mutation. Existing
unowned or malformed Plane entries refuse setup/removal. Private target-bound
backups support restore; connector failures preserve staged/unrelated settings.
Existing Pi/Codex semantics remain unchanged.

## Preservation and migration

Adoption is fail-closed. Retirement metadata for Graphify, RepoWise, ui-craft,
Dembrandt, Argent, Numasec and OpenSpec is preflighted before source publication
or cleanup. Receipt-owned legacy wiring is archived in private backups; custom or
ambiguous registrations, nonempty legacy memory/process receipts, malformed
configs, symlinked destinations and custom policy markers require manual
reconciliation with an actionable error. Historical sessions, memory stores,
indexes, auth, hooks, models and unrelated settings are not deleted or rewritten.
Multi-file wiring writes use ownership receipts, private recovery manifests,
permission preservation, concurrency checks and rollback. Unrelated third-party
installer work is not falsely represented as an atomic rollback.

Pi-owned shared skills are excluded from Pi discovery when harness-specific copies
are installed, preventing duplicate MEGAI skill resolution. Codex/CC/OMP retain
their native/shared destinations and explicit filters. User opt-outs remain in
force and inactive resources are reported honestly.

## Appllama mobile design

Pi bundles the pinned [Appllama design skill](skills/appllama-app-design-skill/SKILL.md)
for Expo / React Native UI, with reviewed upstream references, MIT license and a
permission-aware Pi wrapper. MCP, paid services, simulators and research skills do
not start automatically. Existing filters and other harnesses remain unchanged.
[Provenance](skills/appllama-app-design-skill/PROVENANCE.md) records the retained
standalone bytes. Identical manual installs can be adopted; MEGAI update/removal
uses receipt-owned wiring without fetching upstream or overwriting custom edits.

## Acceptance and task delivery

Pi's [acceptance gate](pi-skill/acceptance/SKILL.md) freezes criteria, captures
source-bound command/runtime evidence and requires independent Pi review before
`megai acceptance check` can return PASS (0). Failed checks return FAIL (1);
missing/stale evidence returns BLOCKED (2). `collect` produces a BLOCKED draft,
never an automatic approval. Schema-2 bug fixes require captured red → green
regression evidence. See the [CLI and trust limits](pi-skill/acceptance/reference.md).

Use only existing Paseo projects: project → task workspace → agent tabs. Resolve
`projectId` with `megai workspace --root FOLDER`, create the appropriate task workspace
under that ID, then pass its verified `workspaceId` to `create_agent`. "Canonical"
means that existing project identity, not a new project or a rename. Missing or
ambiguous identity blocks creation; ask the user rather than register a replacement.

A task spanning backend/frontend/mobile Git repos uses one umbrella project/task
and one managed worktree per affected repo, all named with the same task slug/branch
from each repo's `dev`. Native Paseo accepts `isolation: "worktree"`, the existing
umbrella `projectId`, and `path` pointing to each absolute primary repository.
Do not register child repos as projects. Writers run in their verified workspaces.
Local workspaces remain for coordination/readers and Git-free configuration scopes
with one writer/private backups; local Git writer scopes and broad scopes containing
nested Git are rejected. Local labels declare scope, not a filesystem sandbox/lock.
Independent review and acceptance remain required:
`megai acceptance --help` lists commands; pass the complete configuration directory
as `--root` to snapshot/run/collect/check without Git (all entries included; bounded
to 10,000 entries/64 MiB; unsupported/symlink/nested Git source is rejected).
See the [local-work procedure](skills/agent-worktree-lifecycle/SKILL.md#non-git-local-work).
Reload Pi after installing the guard/policy update; an already-running session keeps
its previously loaded extension until reload.

Require every affected repository's acceptance and cross-repo checks before the
first dev mutation. Reserve all integration targets atomically with `megai queue`
(the separately delivered queue component), then integrate into each repo's dev.
Preserve queue order and partial-delivery evidence; multi-repo merges are not atomic.
Main requires separate user approval of the exact reviewed repo/commit vector;
queue acquisition grants no push/main authorization. Close only released, safely
delivered workspaces/branches; retain dirty work and one primary workspace at rest.
The [lifecycle skill](skills/agent-worktree-lifecycle/SKILL.md) owns the procedure.

## Verification

Focused, non-live checks use disposable HOME/config roots and do not execute
non-Pi harnesses or send provider calls:

```bash
python3 -B tests/slim_distribution.py -k appllama
python3 -B tests/acceptance_gate.py
python3 -B tests/acceptance_flow.py
bash tests/slim-distribution.sh
python3 tests/headroom_wiring.py
HEADROOM_TEST_PYTHON="$HOME/.megai/venv/headroom/bin/python" \
  HEADROOM_TEST_ASSETS="$HOME/.megai/headroom-assets" \
  python3 tests/headroom_runtime.py
bash tests/plane-mcp.sh
bash -n bin/megai lib/*.sh install.sh
python3 -m py_compile lib/*.py pi-skill/headroom/*.py
ruff check --no-fix --no-fix-only --force-exclude --no-cache -- lib/*.py pi-skill/headroom/*.py tests/*.py
 git diff --check
```

The Pi extension suites require an explicitly selected local Pi package via
`PI_PACKAGE_ROOT`; they use disposable settings and a fake/no-provider bridge.
Actual local Headroom runtime tests may read already-installed assets but write
only disposable test storage. No live CC/Codex/OMP execution is part of this
verification.

See `docs/audits/headroom-migration.md` for the concise source/conflict decision
record and run evidence. It records only evidence produced in this checkout; no
host install, nonexistent review or main promotion is claimed.
