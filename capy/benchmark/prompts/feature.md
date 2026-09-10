You are a benchmark leaf worker in a clean, isolated MEGAI checkout. Use the already selected GPT-6 Astra/high configuration; report a mismatch or unavailable prerequisite instead of substituting a model. Parent owns Plane item AS4DABD7BE-45 (project 59005e36-ecd4-46ed-bb42-f779858b20ce, item d791f0e7-aac6-42d8-bf52-ea28b79441fc). Do not mutate Plane, delegate, commit, push or merge. Repository and host safety rules still apply.

Task: implement chunked in capy/benchmark/cases/feature/batching.py to satisfy section 2 of capy/benchmark/tasks.md. Those public seams are user-approved. Read only this task's implementation, tests, applicable instructions and contract; do not inspect other trials or solutions. Add focused tests in capy/benchmark/cases/feature/test_participant.py.

Write authority: only those two implementation/participant-test paths. Acceptance tests, contracts, prompts, manifest and other files are immutable. Standard library only; no installs, network or live app testing. Start a wall clock when this task arrives; include tool/model waits. At 300 seconds return a checkpoint with completed checks and blocker; preserve and report any in-flight write. Do not continue the trial or retry with another model.

Run from the repository root:
python3 -B -m unittest discover -s capy/benchmark/cases/feature -p 'test_*.py' -v

Return in at most ten bullets: verdict, changed paths, commands with raw test summary/exit statuses, elapsed time and its measurement source, model/thinking evidence, scope check and blockers. Report token/cost counters only if the host exposes them; otherwise unknown. Leave the diff uncommitted for the evaluator. Stop at verified acceptance.
