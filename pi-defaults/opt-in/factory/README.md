# Factory: opt-in Brokan long runs in Pi

Factory runs one verified repository’s `doing`, then `todo` tasks in board order, one at a time. It takes an initial snapshot and rereads each task before starting or continuing it. The selected Pi model and thinking level do not change. Factory itself only reads Brokan; the agent uses the existing Brokan tools and repository workflow for edits, acceptance, delivery and `review`. Factory does not set `done`, start without a request, or run a background process.

## Setup (Pi 1.5.2)

Copy this directory to `~/.pi/agent/extensions/megai-factory/` (do not overwrite an existing local copy without backing it up), then use `/reload` or restart Pi. This is not installed by default. The local Brokan web API on `127.0.0.1:1317` and existing Brokan tools must be available. Start from the trusted Git checkout, not a scratch chat. By default the GitHub `origin` repository name must match the Brokan slug, and the full owner/repo must be linked in Brokan. If the link is missing or the slug differs, add `"brokanProject": "your-slug"` to the root `.pi/project.json`. A project named in the invocation must still match the binding.

## Run and stop

- `/factory`: take a batch from the current repository’s project.
- `/factory your-slug#123`: run just that task if eligible. `/factory your-slug` uses the same project-wide batch as `/factory`.
- Plain prompt: `factory run`, `factory run your-slug#123`, or `Brokandagi todo va doing tasklarni oxirigacha bajar`. Other prompts do not start Factory.
- `/factory status` shows the current task and queue; `/factory stop` or Esc stops. User input mid-run takes over from Factory, and UI prompts halt automatic continuation.

Factory skips human tasks, archived projects, and all other columns. It hands off on a readback of `review` or `done`, pauses on a real blocker or a board error, and gives an unfinished task at most three automatic continuations. A batch is the eligible queue as it stood when you started; run `/factory` again for newly added tasks. Other manual agents are not covered by the Factory lock: do not run it against work another agent is actively editing. A hard process kill can leave a lock under `~/.pi/agent/factory-locks/`; remove only that project's lock after verifying its recorded PID and that the owning run is no longer active. Reloading or restarting Pi never automatically resumes a batch.
