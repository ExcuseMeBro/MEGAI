# MEGAI test guard

A counter-metric for autonomous delivery. An agent judged only by green tests can get
there by weakening the tests. This Pi `tool_call` hook checks every `bash` call that pushes
to `dev`, including calls made from `codemode` scripts, and every `ipython` cell whose
visible shell commands push to `dev` (`bash('…')`, `os.system('…')`, subprocess argv lists
such as `["git", "push", "origin", "dev"]`). Like the ipython action-boundary bridge this is
advisory for cells: computed strings (f-strings, concatenation, `eval`) are not visible.
Claude Code and Codex get the same check as a `PreToolUse` hook through
`megai-agent-sync` (see `docs/agent-sync.md`). It diffs the pushed range
(`<remote>/dev..<source>`) and blocks the push when the range:

- adds a skip, focus or xfail marker to an existing test file (`it.skip`, `.only`, `xit`,
  `@pytest.mark.skip/xfail`, `self.skipTest`, `t.Skip`, `#[ignore]`, `@Disabled`, …),
- deletes a test file without deleting any non-test source in the same range,
- removes at least 5 net assertions from a test file while keeping under a quarter of them,
- makes CI tests non-blocking (`continue-on-error: true`, `allow_failure: true`,
  `test … || true`, `--passWithNoTests`).

These are not flagged: skips gated on the environment ("…_DSN not set", `skipUnless`,
platform checks, Playwright's `test.skip(condition, …)`), new test files, and prose in docs.

The model sees the findings and is told to make the code pass the original tests. When the
test change is itself correct, a commit in the range carries a trailer
`Test-Change: <why>`, and the push goes through. The reason stays in Git history for review.

On the last 300 commits of nine local repositories it flagged 7 of 1287 commits (0.5%).
All 7 really removed or skipped tests (retired features, removed live tests).

- `MEGAI_TEST_GUARD=0` disables it.
- It reads Git only (`rev-parse`, `log`, `diff`, 15 s timeout each). It never edits,
  retries or pushes. A git error, an unknown ref or a path given as a variable
  (`cd "$repo"`, `"$SHA":refs/heads/dev`) lets the push through. This is a guard, not a
  CI gate.

## Diff budget

A second counter-metric limits change size. When a budget is active, a push to `dev` that changes more lines than it allows is blocked. The count is added plus removed lines in `git diff --numstat <merge-base>...<source>`, with lockfiles (`package-lock.json`, `Cargo.lock`, `go.sum`, …) and binaries excluded. The model is told to push the most valuable part within the budget, or nothing, and leave a note. A `Test-Change:` trailer does not lift it.

- Factory sets the budget for a routine task with `maxDiffLines` while it runs that task (see the Factory README). It is shared in-process as `globalThis[Symbol.for('megai.diff-limit')]`.
- `MEGAI_DIFF_LIMIT=<lines>` sets one for a manual session.
- `MEGAI_TEST_GUARD=0` disables both checks. Errors fail open, as above.

## Factory review gate

While Factory runs with its [independent review gate](../../opt-in/factory/README.md#independent-review-gate), it publishes the approved changes as `globalThis[Symbol.for('megai.review-gate')] = { label, approved: [patch-id] }`. A push to `dev` then passes only when the stable patch-id of its change (`git diff -U0 <remote>/dev...<source>`, no renames, full index) matches an approved one. The base is the destination tip read with `git ls-remote` (it must already be fetched), not the local remote-tracking ref, so rewriting that ref cannot hide unreviewed commits. A clean rebase keeps the id; anything changed after the review does not. The hook sees a call before it runs, so while a gate is active the dev push must be its own `bash` call: only `cd`, read-only Git (`fetch`, `status`, `log`, `rev-parse`, `merge-base`, `show`, `diff`, `ls-remote`) and text filters may share it, with no command substitution or background job, and a dev push from `ipython` is refused. Unlike the other checks this one fails closed: a dev push whose directory or range the guard cannot read is blocked. Inside a Factory preparation worker (`MEGAI_FACTORY_PREP_WORKER=1`) every dev push is blocked. `git push origin HEAD`/`@` on dev and `--all`/`--branches`/`--mirror` count as dev pushes for every check. Outside a gated Factory run nothing changes. `MEGAI_TEST_GUARD=0` disables this check too. Claude Code and Codex hooks run in a separate process and never see a gate.
