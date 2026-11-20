---
name: megai-change-review
description: Independent pre-delivery review of a committed code change — merge risk, change stack reading order, blast radius from external input to sinks, and at most 8 severity-ranked findings that passing tests miss. Use after tests pass and before delivering any non-trivial agent-written change; pairs with diff-security.
---

# Change review

Goal: catch what green tests miss, before delivery, without the author grading their own work.
The author's context is biased toward its own plan, so the review runs in a **fresh, read-only Pi
process** that sees only the goal, the diff and the repository.

## When

- After the task's tests pass and the change is committed in the task worktree, before sync/merge/push.
- Skip only for docs-only or single-line mechanical changes; say "review: skipped (docs-only)".

## Run

From the task worktree root:

```sh
node ~/.pi/agent/skills/megai-change-review/review.mjs --base <remote>/dev --goal-file <acceptance.md> --fail-on high
```

- `--base`: the branch the task started from (`origin/dev`, or the snapshot branch such as `origin/for-ustama`).
- `--goal-file`: the Brokan task's scope and acceptance criteria (no secrets). Without it the commit messages are the goal.
- `--model`: default `openai/gpt-6.2-sol:high`. Name another model explicitly if you need one, for example a second
  reviewer from a different model family for a **High** risk change. Never substitute silently.
- `--packet-only`: build the packet and stop (to inspect what the reviewer will see).

The packet orders files into a change stack (contracts → core logic → wiring/I/O → UI → tests → docs), drops lockfiles
and generated files, cuts large diffs (20k chars per file, 120k diff, 140k packet; the reviewer reads the rest itself)
and redacts secret-looking lines and private-key blocks in every section (goal, stat, diff). Packet and report are
written `0600` into a fresh temp folder.

Isolation: base and head are pinned to SHAs once; Git runs without external diff, textconv or fsmonitor helpers. The
reviewer works in a clean `git archive` export of the pinned commit (no untracked, ignored or uncommitted files), with
`--offline --no-approve --no-extensions --no-skills --no-context-files --no-mcp` and only `read,grep,find,ls`. The model
must be an exact `provider/id` row in `pi --list-models`, so a fuzzy pattern can't pick a different reviewer.
Residual risk: `read` still accepts absolute paths outside the export; the reviewer has no write, shell or network tool,
and its provider is the one the author session already uses.

Exit codes: `0` report written; `3` a finding at or above `--fail-on`; `2` setup error or malformed report (rerun once;
if it fails again, review the diff yourself with the same template and say so).

## Act on the report

1. Read `report.md`. Treat every finding as a claim to verify in code, not as a fact.
2. For each **critical/high** finding that holds: write the failing test first, then the smallest fix, rerun affected tests.
   If it does not hold, write one line of evidence (file:line, test name) why.
3. Medium/low: fix when cheap and in scope; otherwise note it in the Brokan task.
4. Re-run the review only when the fix changed behavior beyond the finding.
5. Record one line in the delivery note / Brokan comment:
   `review: risk <R>; <n> findings (<k> high) — <fixed / rebutted / noted>; reviewer <model>; head <sha>`.

The report format (risk line, change stack, blast radius, ranked findings with where/scenario/tests/fix, verdict) is
fixed in `review-core.mjs` so reports are comparable across tasks.
