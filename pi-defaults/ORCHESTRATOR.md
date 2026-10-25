# Opt-in all-project Plane orchestrator

`orchestrator.py` is a **separate, opt-in** runner, not `/factory` and not an installed background service. It inventories every accessible Plane project and each project's Todo/Needs You tasks using complete paginated reads. One task-owned Pi session per Plane project/task UUID is stored privately and reopened with the *same* session ID after a reply. It works on one task at a time and keeps going after a question. It never declares the queue empty when an unmapped, blocked, foreign In Progress, or waiting task remains.

## Prerequisites and operator decisions

1. Confirm the connected Plane workspace, project→primary repository mappings, and an operator's **member UUID**. No guessed repo mapping or cross-project identity substitution. Every project with Todo work needs an explicit mapping. A multi-repo task still follows its project's `.pi/project.json` and normal per-repository delivery policy.
2. Have a working `pi-bolt` and `pi-workflow context` for each mapped repository, Plane MCP credentials, and task acceptance. Do not install or repair runtime helpers as a side effect of running the orchestrator. The current local `pi-workflow` launcher was observed to reference a missing `~/.pi/agent/defaults/workflow.py`; fix and verify that separately before live runs.
3. Decide the provider/model budget and *explicitly* opt in to bounded model runs. The runner does not auto-start on boot, schedule itself, or grant main, publishing, Done, force-push, foreign cleanup, or session termination. Apply the stricter project-specific delivery rules. It does not bypass any formal acceptance gate or browser evidence already required by a task.
4. Prepare an owner-only private directory **outside every Git repo**, for example `mkdir -m 700 ~/.local/state/plane-orchestrator`. Put a JSON config there (`chmod 600`). The runner owns only its own subprocess sessions; if a worker is active, ownership uncertain, or an update failed mid-flight, it stops and leaves that task for manual reconciliation, never silently replays a write.

Example config (replace placeholders with verified values, include **all** intended projects):

```json
{
  "operator_id": "00000000-0000-4000-8000-000000000000",
  "private_dir": "/ABSOLUTE/PRIVATE/DIRECTORY",
  "projects": {
    "PROJECT-UUID": "/ABSOLUTE/PRIMARY/GIT/REPOSITORY"
  }
}
```

Dry inventory (no Plane writes, no model calls):

```sh
python3 pi-defaults/orchestrator.py --config /ABSOLUTE/PRIVATE/DIRECTORY/config.json
```

Explicitly bounded run, without leaving a daemon behind:

```sh
python3 pi-defaults/orchestrator.py --config /ABSOLUTE/PRIVATE/DIRECTORY/config.json --run --max-runs 3
```

Foreground polling while there are pending owner answers (stops at the model-run cap or when no work remains):

```sh
python3 pi-defaults/orchestrator.py --config /ABSOLUTE/PRIVATE/DIRECTORY/config.json --run --serve --max-runs 3 --poll-seconds 60
```

**Do not launch `--serve` or register a startup job without a separate explicit activation/spending decision.** `--max-runs` bounds new model invocations, not their token cost or the time spent awaiting replies. If a task needs your input, the runner creates/verifies its project's `Needs You` state, posts one precise question and marks only that task. Reply **in a new comment** with `!answer your answer` (the prefix is necessary when the bot's Plane token uses the same account as yours). The next running foreground pass checks comment author, timestamp, origin and prefix, moves that item to In Progress, and supplies the answer to its previous *task-specific* Pi session. Ordinary comments, edits, bot comments and other users' replies do not resume it. The next independent Todo task may proceed in the meantime. A task-local non-question blocker stays In Progress with a private ledger reason; independent Todo work continues, but the blocked task must be reconciled explicitly.

A runner crash during a model call or uncertain Plane write leaves `starting`/`running`/`posting`/`resuming` in `ledger.json`. **Do not delete the ledger or rerun the task to bypass this.** Inspect the actual Pi session, task, comment and dev/remote state before deciding how to reconcile. A reviewed result is accepted only when the exact Plane task is already In Review; the worker must supply its own check/test/delivery evidence under existing project rules. The runner cannot safely rescue a foreign active session or a worker with ambiguous ownership.
