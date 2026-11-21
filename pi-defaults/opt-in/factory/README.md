# Factory: opt-in Brokan long runs in Pi

Factory runs one verified repository’s `doing`, then `todo` tasks in board order, one at a time by default. It takes an initial snapshot, rereads each task before starting or continuing it, and rereads the board when the batch runs dry, so tasks added meanwhile run in the same batch. The selected Pi model and thinking level do not change. Factory itself only reads Brokan, except that it adds the tasks of due [routines](#routines); the agent uses the existing Brokan tools and repository workflow for edits, acceptance, delivery and `review`. Factory does not set `done`, start without a request, or run a process outside Pi. Watch mode keeps checking Brokan only inside the Pi session where you start it.

## Setup (Pi 1.5.2)

Copy this directory to `~/.pi/agent/extensions/megai-factory/` (do not overwrite an existing local copy without backing it up), then use `/reload` or restart Pi. This is not installed by default. The local Brokan web API on `127.0.0.1:1317` and existing Brokan tools must be available. Start from the trusted Git checkout, not a scratch chat. By default the GitHub `origin` repository name must match the Brokan slug, and the full owner/repo must be linked in Brokan. If the link is missing or the slug differs, add `"brokanProject": "your-slug"` to the root `.pi/project.json`. A project named in the invocation must still match the binding.

## Run and stop

- `/factory`: take a batch from the current repository’s project.
- `/factory your-slug#123`: run just that task if eligible. `/factory your-slug` uses the same project-wide batch as `/factory`.
- Plain prompt: `factory run`, `factory run your-slug#123`, or `Brokandagi todo va doing tasklarni oxirigacha bajar`. Other prompts do not start Factory.
- `/factory parallel`: prepare up to five tasks at once. Use `/factory parallel 2` through `/factory parallel 5` to set the width, or the equivalent plain prompt `factory run parallel [2–5]`.
- `/factory watch`: keep Factory armed in this open Pi session (see below). `/factory watch parallel [2–5]` and `/factory watch your-slug` work too, and so do the plain prompts `factory watch`, `brokanni kuzatib bajar` and `brokandagi yangi tasklarni avtomatik bajar`.
- `/factory status` shows the current task and queue; `/factory stop` stops. Esc also interrupts an active Pi turn; use `/factory stop` while the first parallel wave is preparing. User input mid-run takes over from Factory, and UI prompts halt automatic continuation.

Factory skips human tasks, archived projects, and all other columns. It hands off on a readback of `review` or `done`, pauses on a real blocker or a board error, and gives an unfinished task at most three automatic continuations. A batch ends when the board has no eligible task it has not already tried in that batch; a task is not repeated within one batch. Other manual agents are not covered by the Factory lock: do not run it against work another agent is actively editing. A hard process kill can leave a lock under `~/.pi/agent/factory-locks/`; remove only that project's lock after verifying its recorded PID and that the owning run is no longer active. Reloading or restarting Pi never automatically resumes a batch.

## Watch mode

Watch mode runs every eligible `doing`/`todo` task, then waits in the open Pi session. When a task is added to `todo`, or moved there or to `doing`, it starts a new batch automatically. Pi must stay open, for example in a terminal tab or a T3 thread you leave running. Closing Pi, `/reload`, a new session or a restart ends watching, and it never resumes by itself.

- While idle it reads only the local `GET /api/changes` token, every 30 seconds by default (`MEGAI_FACTORY_WATCH_SECONDS`, 0.05–3600). It reads the board only when that token moved. The project lock is held only while a batch runs.
- A task that ends with `FACTORY_PAUSE`, hits the continuation limit or fails a readback is skipped. It runs again once its Brokan record changes (`updated_at` or its comment count), for example after you edit it or comment on it. Then the rest of the queue continues. `/factory status` shows how many tasks are skipped.
- In parallel watch mode, a worker failure or an unverified delivery stops watching, because retained worktrees need inspection.
- Watching stops on `/factory stop`, typed input, an extension UI prompt, Esc during a Factory turn, or session shutdown. Board errors and a lock held by another session are reported once, and checking continues.

## Parallel preparation

Use parallel mode only when the eligible tasks are independent Git changes in the same repository. It needs POSIX, `pi` on `PATH`, a reachable `origin/dev`, and the selected provider/model and Brokan tools available to fresh Pi processes without project-local approval. All workers use the current Pi provider, model and thinking level; this mode can use several model requests concurrently. It does not start automatically.

Each worker prepares one task in its own `task/factory-<slug>-<id>` branch and worktree under `~/.pi/agent/factory-worktrees/`. Workers do not deliver. The parent Pi verifies and integrates each prepared branch to `dev` **one at a time**, in queue order, including remote verification, cleanup and Brokan readback. The next wave starts only after that handoff. Workers share the host and must honor the repository's shared heavy-test lock and resource rules; worktrees are not security sandboxes.

A blocker, worker failure, model change or cancellation stops further dispatch and leaves any unfinished worktrees in place. There is no on-disk transcript for the preparation workers in this mode. Inspect the retained branch/worktree and the Brokan task before restarting or continuing manually. Check scope and that no other agent owns the work before resuming.

## Lessons

When you send a task back from `review`, the comment you leave in Brokan becomes a project lesson. This keeps the same correction from being needed twice.

- When Factory takes a `todo`/`doing` task, it reads the task's comments. Comments written in the Brokan web UI (author `me`) after an agent comment count as review feedback. Each one is appended once to `~/.pi/agent/lessons/<project>.md`. Your comments made before any agent comment are scope notes and are not saved.
- The task instruction then tells the agent the task came back, and to address each point and say how in its evidence note.
- Every Pi session whose trusted checkout is bound to that project gets the newest 20 lessons (at most 4,000 characters) appended to its system prompt. This covers Factory runs, parallel workers and ordinary prompts. They are framed as guidance, not tasks or authority over other rules.
- `/lessons` lists them with numbers. `/lessons add <text>` adds one, `/lessons forget <n>` removes one, and `/lessons sync` saves feedback from every commented task of the project (read-only on Brokan). The file is plain Markdown: one `- ` line per lesson, and you can edit it directly.
- An MCP client could also write a comment with the author `me`. Lessons are local and advisory, so review the file if a project has many agents writing comments.

## Routines

Routines are recurring work, for example a weekly dependency refresh or flaky-test sweep. Each one becomes an ordinary Brokan task that Factory then runs.

- `/routines init` writes a disabled example to `~/.pi/agent/routines.json`. Each routine has:
  - `id` and `project` (slugs) and `title`;
  - an optional `description`, the task body and its acceptance;
  - `every`: `daily`, or `weekly` with `day` (`mon`…`sun`);
  - `at`: local `HH:MM`, default `09:00`;
  - an optional `maxDiffLines`;
  - `priority`, default `low`;
  - `enabled`.
- When a slot has passed, the next Factory start (`/factory`, `/factory parallel`) or watch check for that project adds one `todo` task tagged `routine` and `routine:<id>`. A routine whose previous task is still open (`todo`, `doing` or `review`) is skipped for that slot rather than duplicated. A newly enabled routine runs at the next check. Nothing runs while Factory is not running or watching; with `/factory watch`, due routines are added within one check interval.
- State lives in `~/.pi/agent/routines-state.json`. A lock file keeps two Pi sessions from adding the same task.
- **Counter-metric:** `maxDiffLines` is a budget of changed lines (added plus removed against the merge base with `origin/dev`), with lockfiles excluded. The limit comes from local routine state, never from task text. While Factory runs that task, it shares the limit with `megai-test-guard`, which blocks a larger push to `dev`. The agent is told to deliver the most valuable part within the budget and list the rest. Without `megai-test-guard` installed, the budget is only an instruction.
- `/routines` lists schedules, the next slot and the last task. `/routines run <id>` adds that routine's task now (an open one still blocks it), and `/routines tick` checks all projects.
