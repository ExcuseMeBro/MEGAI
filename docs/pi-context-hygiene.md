# Reduce Pi context accumulation without a window cap

Keep native context capacity available for work that needs it. The installed
`megai` skill ([source](../pi-skill/ADAPTIVE.md)) guides bounded discovery, reuse of
current evidence and user-controlled session handoffs. It does not enforce a token
limit, rewrite requests, delete history or change models, thinking, skill selection
or native compaction settings. Existing safety and acceptance requirements remain.
The existing bootstrap loads this skill; no additional always-loaded pointer or
extension is needed.

## Daily use

- **Independent task:** use `/new`. Bring the goal, constraints and relevant paths,
  not the preceding conversation. `/fork` and `/clone` retain history; they are not
  context cleanup. Continue the existing session when its history is still needed.
- **Long ongoing task:** at a completed phase, use `/compact` when older history is
  no longer useful in full. For example:

  ```text
  /compact Keep the goal, constraints, Plane project/item IDs, verified workspace and branch, changed paths, evidence locations, blockers and next action.
  ```

  Summarization itself costs tokens and is lossy. Consult original files and raw
  receipts for exact decisions. Native JSONL history remains on disk. Do not compact
  after every tool call or summarize work solely to produce a cost report.
- **Discovery:** locate files/symbols with scoped `rg -l` / `rg -n`, then read relevant
  ranges and dependencies. Reuse current reads and metadata; refresh on drift,
  failed assumptions or required boundaries. Mandatory full-document reads still
  apply. Complete scoped searches are required for exact/absence claims; truncated
  output cannot establish absence.
- **Output:** retain full logs on disk and inspect the relevant ranges. Passing
  results can share the same raw receipt across required handoffs; preserve failures,
  security checks and acceptance evidence. UI folding hides output visually but
  does not remove it from model context.
- **Resources and agents:** load matching skills and disclose references on demand.
  Preserve explicit resource choices. Routine work uses direct parent tools and
  focused verification under the existing MEGAI policy; required guarded review and
  configured economy routing are unchanged. A necessary child gets a bounded task
  and evidence references, not a full conversation by default.

A handoff is needed only when changing sessions or owners. It carries the goal,
constraints, Plane pair, verified workspace/branch, changed paths, evidence
references, blockers and next action; it is not a second task board.

## Activate locally

Install the reviewed `pi-skill/ADAPTIVE.md` as
`~/.pi/agent/skills/megai/SKILL.md` and refresh its canonical
`~/.megai/pi-skill/ADAPTIVE.md` copy using existing ownership-checked installation
with private backups. Preserve unrelated local files and ownership receipts.
If an owned destination has changed, reconcile it rather than overwriting it.

Use `/reload` to refresh resources in interactive Pi, or start a fresh session.
Reload does not remove accumulated conversation history or prove a running agent
has re-read the skill. Keep the current work intact until its handoff is complete.
This workflow does not apply the separate optional
[context budget](pi-context-budget.md).

## Verify honestly

For policy-only changes, inspect the diff and verify installed-source parity plus
fresh native skill discovery. Confirm settings/models and unrelated instructions
are unchanged. No provider request or new benchmark task is necessary to install.

On subsequent comparable real tasks, compare acceptance and corrections alongside
request count, average input context, output, cache reads/writes and billed usage.
Use explicit task boundaries and include required child/summary usage when available.
Cached input still counts toward reported tokens; token totals are not necessarily
billed cost. A cheaper model or shorter final response alone does not remove a
large inherited input context. No percentage reduction is guaranteed by this policy.
