# Acceptance CLI and evidence

## Scope and trust

`megai acceptance` uses Python's standard library and Git; it does not launch an
agent, install a browser, call Plane, start a server, or grant new permissions.
Pi's installed workflow selects existing project commands and coordinates the
independent verifier. Only a trusted parent or CI job should assemble final
contracts/evidence. Model metadata and observations are attestations: the checker
validates consistency, not the authenticity of an external Paseo response.

The checker is not an adversarial security boundary. Anyone able to replace the
runner, approved CLI hash or all local evidence can forge a local PASS. Protect
contracts, evaluator and evidence from participant writers; fetch the approved
hash independently from Plane. A repository can require this command in CI and
protect that CI check, but this package does not modify branch protection or
intercept arbitrary Git pushes. Do not equate a prompt with enforced merge policy.

Source fingerprints cover Git HEAD, index blob IDs/modes and tracked/nonignored
untracked content, including deletions/modes. Ignored build outputs, dependencies, databases and
external services are not proven by a source hash. Record their versions and
runtime provenance in observations/review. Unsupported source states must be
resolved rather than silently excluded. Commit before final capture if committing
would otherwise invalidate the snapshot. Keep artifacts outside the source tree.

## Commands

Examples use an existing, disposable repository and trusted bounded commands.
Replace paths and commands with the task's actual approved values.

```bash
megai acceptance snapshot --root /path/to/repo
megai acceptance run --root /path/to/repo --out /private/evidence/unit -- python3 -m unittest discover
megai acceptance check --root /path/to/repo \
  --contract /private/evidence/contract.json \
  --contract-sha256 HASH_RETRIEVED_FROM_PLANE \
  --evidence /private/evidence/evidence.json
```

`run` requires a **new** private output directory outside the checkout, with an
existing parent. It refuses reuse rather than overwriting prior evidence. It runs
argv directly, not a shell string; `&&`, pipes and redirections are not shell
syntax here. If a repository requires a shell script, pass its trusted script as
an explicit argument. Never put credentials in argv. Raw combined stdout/stderr
is retained in `output.txt`, with `receipt.json` beside it. Inspect raw failures;
a summary is not a replacement for the original output.

The runner does not kill commands at a deadline: killing a live mutation can harm
data integrity. Choose bounded checks (configure timeouts in the test tools), not
an indefinitely running dev server. Start/stop application services separately
under the project's authorized lifecycle. A five-minute agent checkpoint is not
a subprocess watchdog. Interrupted/unfinished runs without complete receipts are
BLOCKED; reconcile their outcome before retrying.

`check` is read-only. Machine JSON and process status distinguish:

| Status | Exit | Meaning |
| --- | --- | --- |
| PASS | 0 | Every declared criterion and review has complete current evidence |
| FAIL | 1 | A required executed check or reviewer reported failure |
| BLOCKED | 2 | Missing, malformed, stale, unauthorized or inconsistent evidence |

`run` uses the same status mapping but retains the child's original exit code in
its receipt. A runner PASS proves command completion/source stability, not full
task acceptance: always perform final `check` with the independent review.

## Contract (schema 1)

Start from [contract.example.json](contract.example.json); it is only an example,
not a pre-approved task or live-testing authorization. Required fields:

- `plane`: `project_id` and `work_item_id` UUIDs of the existing task.
- `implementer_session_id`: the real implementer's session identity.
- `runtime`: `required`, `authorized`, `environment` (`local`, `staging`, `none`),
  `targets` and `reason`. Required runtime checks need explicit authorization,
  a local/staging environment and approved targets; production is unsupported.
  If runtime is unnecessary, provide a task-specific reason.
- `criteria`: a nonempty list with unique `id`, `kind` (`test` or `runtime`),
  `expected` observable outcome and exact `command` argv. Runtime entries also
  require `target`, matching an approved runtime target.

Runtime target strings constrain the contract/evidence, not arbitrary command
network access. The coordinator must verify command behavior and use isolated
test accounts/data. Backend outcomes and browser state must be actually observed;
commands that return zero without asserting the requirement are inadequate.

Freeze the raw contract bytes: whitespace changes also change SHA256. Store the
approved hash with the task's acceptance in Plane before edits. Do not calculate
a fresh replacement hash at handoff merely to make a changed contract pass.

## Evidence (schema 1)

The evidence file is external to the source checkout. All artifact and receipt
paths are relative to its parent, except `receipt.log.path`, which is relative to
the receipt's directory. Use regular files, not traversal or symlink escapes.

Top-level fields:

- `schema`: `1`.
- `contract_sha256`: externally approved hash.
- `snapshot`: current candidate source fingerprint.
- `checks`: exactly one entry per criterion, no extras or duplicates.
- `review`: source-current independent Pi review.

Each check contains `id`, `status` (`PASS`, `FAIL`, `BLOCKED`), a nonempty
`observation`, `receipt` (path to the actual runner receipt), and `artifacts`
(a list, possibly empty, of `{ "path": "relative/file", "sha256": "..." }`).
Store browser screenshots, traces or API observations here when required.

Each runner receipt binds `argv`, `cwd`, `snapshot_before`, `snapshot_after`,
`exit_code`, `duration_seconds` and `log: {path, sha256}` under `schema: 1`.
The checker compares argv with the frozen criterion and verifies raw log bytes.
Missing commands and source changes cannot masquerade as successful execution.

The review contains:

- `session_id`: distinct from `implementer_session_id`.
- `harness`: `pi`; `model`: an exact approved GPT model; `thinking`: `high`.
- `verdict`: `PASS`, `FAIL` or `BLOCKED`.
- `snapshot` and `contract_sha256`: the same frozen candidate and contract.
- `criteria`: every criterion ID exactly once.
- `artifact`: `{path, sha256}` for the actual review/status evidence.

Save the review together with observed Paseo status metadata after neutral READY
verification; a made-up session/model string is not independent review. Review
artifacts should identify findings and affected criteria. The parent is responsible
for authenticity and adequate observations, including correct running-build
provenance. The checker cannot infer UI correctness from pixels or log prose.

## Delivery and installation

The CLI is bundled with MEGAI; receipt-owned Pi wiring installs the acceptance
skill and references without changing other harnesses or native model settings.
Existing explicit skill exclusions still win: report an unavailable gate rather
than claiming automatic activation. A repository commit does not install resources
into an already-running local Pi session; authorized update/wiring and reload are
separate operations. No host installation is implied by branch delivery.
