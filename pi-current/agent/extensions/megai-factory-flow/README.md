# Factory Flow for Pi

A read-only companion to Brokan task ownership and Pi worktree delivery. It neither replaces `/factory` where installed nor registers an execution tool, writes to Brokan, starts a model turn, subscribes to events or launches workers.

## Install

Use Pi 1.5.2 (the verified runtime) with Node 22 or later. Copy this directory as `megai-factory-flow/` into your user Pi `extensions/` directory (default `~/.pi/agent/extensions/`). Start a fresh Pi session; `/factory-flow help` should appear. If you use deny-by-default extension selectors, explicitly allow this extension's `index.ts`. To disable it, remove that entry or move this directory outside the extension directory. Do not overwrite an existing extension of that name without checking its contents. No provider, model, thinking level, MCP credentials or other settings need to change.

Run from a Git repository with an explicit, top-level `.pi/project.json` such as `{"brokanProject":"demo"}`. Otherwise, `origin` must be a GitHub repository explicitly linked to the matching active Brokan project. Other hosts use the explicit binding. The extension reads loopback Brokan at `127.0.0.1:1317`; if it cannot read the board, it does not infer state. It has no background work or network requests until a command is entered.

## Daily use

| Command | Reads |
| --- | --- |
| `/factory-flow needs` | Decision, missing access or spec, and resource or check waits; only a bounded top-of-board view of agent-owned `todo`/`doing` tasks. |
| `/factory-flow ready` | Same queue, dependencies satisfied at `review` or `done`, no open handoff, and records available. Missing/invalid dependencies and cycles block readiness. |
| `/factory-flow resume demo#42` | Open questions, recorded answers and the next step in a fresh session. An answer shown from a task is not authorization. |
| `/factory-flow receipt demo#42 FULL_SHA` | Checks for exactly that commit and the remote attestation, if covered. This does not fetch Git, prove ancestry or replace formal acceptance. |
| `/factory-flow eval PATH` | Quality, regressions, median latency, head-to-head speed wins and median cost over complete cost pairs, from an explicit local JSON file. |

`needs`/`ready` look at up to 24 candidates and inspect up to 16 comment-bearing tasks. `ready` can look up up to 12 missing dependencies if the board hides old completed work. Views label partial/unknown results; use `resume` for a specific task. Before dispatch, reread the task, ownership, dependency gates and approvals, then use the existing task-owned worktree and single delivery owner. No automatic continuation follows an answer. In OpenBot, ask the concrete question using its existing confirmation/answer flow; use Brokan or the Brokan MCP to record a non-secret answer and leave approval with the user. For repeat measurements, use matched input/setup fingerprints and report quality before speed or price. Nothing here runs an eval or estimates its cost.

### Pilot with OpenBot and Pi

1. In the assigned Brokan task, the delivery owner records one wait and its next step. In OpenBot, the owner asks the question using the normal approval/answer card; record only the needed, non-secret outcome in the task after the user answers.
2. In a fresh Pi session, use `resume` to recover the handoff; re-read Brokan ownership and the applicable approval before acting. Use `ready` to spot tasks that can be reviewed for a separate worktree, not to authorize parallel execution.
3. Run the task's frozen checks on the actual candidate and write a candidate receipt. After Git verification, update the receipt for that same SHA. If the SHA changes, run the applicable checks again.
4. For a prompt/model A/B replay, choose historical tasks with preserved acceptance gates and sanitized inputs. Fix the same base and shared environment; isolate each run and alternate the A/B order. Record all results, including failures. Compare accepted pairs and regressions before interpreting elapsed time or cost.

## Record format (synthetic examples)

Optional separate lines in the task **description**:

```text
Factory depends-on: demo#40 demo#41
Factory required-checks: test lint
```

Use canonical task IDs in the same project. Only the task owner should author or reconcile these lines. Add these exact, single-line comments via Brokan in chronological order, one comment per record; other comments are ignored. Keep bearer tokens, credentials, private logs and complete chat transcripts out of the board. Decisions/answers are descriptive text, not instructions to execute.

```text
Factory-Flow: {"v":1,"kind":"wait","key":"delivery-target","type":"decision","blocked":"Delivery target not selected","question":"Which test target should be used?","recommendation":"Use the synthetic target","next":"Verify target and rerun tests"}
Factory-Flow: {"v":1,"kind":"answer","key":"delivery-target","answer":"Use the synthetic target"}
Factory-Flow: {"v":1,"kind":"receipt","stage":"candidate","sha":"1111111111111111111111111111111111111111","checks":[{"name":"test","status":"pass"},{"name":"lint","status":"wait"}]}
Factory-Flow: {"v":1,"kind":"receipt","stage":"remote-verified","sha":"1111111111111111111111111111111111111111","remote":"origin/dev","remoteHead":"2222222222222222222222222222222222222222","checks":[{"name":"test","status":"pass"},{"name":"lint","status":"pass"}]}
```

Wait types: `decision`, `access`, `spec` (a person is needed), `resource`, `check` (execution is pending). A question key is unique per task; use a fresh key for a new decision. Create a remote receipt only after the delivery owner verifies the exact candidate is in the intended remote ref, all declared checks pass, and any frozen acceptance has passed. A new SHA always needs new evidence. The command reads the latest receipt for the requested SHA; an earlier green receipt is not reused. The required-check list is advisory metadata, not an amendment to a frozen contract.

### Eval input

Use version `1`, two distinct short `arms`, and 1–200 unique `cases`. Each case has `id` and two `runs`, one per arm. Each run contains `arm`, `base` (full Git SHA), `fixture` (SHA-256 of inputs), `setup` (SHA-256 of shared controls), `accepted` (boolean), `regressions` (nonnegative count), `ms` (positive integer), and `usdMicros` (integer millionths of a dollar, or `null` when unknown). Both runs in a pair must share `base`, `fixture` and `setup`. Only a passed acceptance with zero regressions counts as accepted; unknown cost is not zero. Save only sanitized observations, not model prompts, credentials or transcripts. See the [synthetic native fixture](../../../tests/factory-flow-native.test.mjs) for a minimal input and checked outputs.
