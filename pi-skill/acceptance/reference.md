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
megai acceptance run --root /path/to/repo --out /private/evidence/red \
  --test-file tests/test_reported_bug.py -- python3 -m unittest tests.test_reported_bug
megai acceptance collect --root /path/to/repo \
  --contract /private/evidence/contract.json \
  --contract-sha256 HASH_RETRIEVED_FROM_PLANE --out /private/evidence/candidate
megai acceptance check --root /path/to/repo \
  --contract /private/evidence/contract.json \
  --contract-sha256 HASH_RETRIEVED_FROM_PLANE \
  --evidence /private/evidence/candidate/evidence.json
```

`run` requires a **new** private output directory outside the checkout, with an
existing parent. It refuses reuse rather than overwriting prior evidence. It runs
argv directly, not a shell string; `&&`, pipes and redirections are not shell
syntax here. If a repository requires a shell script, pass its trusted script as
an explicit argument. Never put credentials in argv. Raw combined stdout/stderr
is retained in `output.txt`, with `receipt.json` beside it. Inspect raw failures;
a summary is not a replacement for the original output.

`collect` validates the approved contract and regression baselines before executing
anything. It runs the frozen argv lists once in criterion order, using numbered
subdirectories (criterion IDs never become filesystem paths). It stops at the
first failure, missing executable or source change; remaining criteria stay BLOCKED.
The new private `evidence.json` already contains receipt paths, candidate/hash and
an empty review template. Fill observations only after inspecting raw results, and
fill review metadata/artifact only from a verified independent Pi session. Keep
review artifacts inside the collection directory and hash their actual bytes.
No contract is auto-approved, no failed command is auto-retried, and no observation
or reviewer identity is invented. A completed collection returns **BLOCKED/2** until
those human/agent attestations exist; an executed command failure returns **FAIL/1**.
Always use `check` for the final verdict. `collect` never returns acceptance PASS.
A new collection uses a new directory; retain old failures rather than overwrite.

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

## Contract (schema 2; schema 1 remains readable)

Start from [contract.example.json](contract.example.json); it is only an example,
not a pre-approved task or live-testing authorization. New tasks use schema 2.
Schema 1 remains supported for existing frozen contracts; it cannot represent a
mandatory bugfix regression. Never downgrade a bugfix to bypass the new gate.
Required fields:

- `schema`: `2`; `task_type`: `bugfix`, `change` or `docs`. A `bugfix` requires at
  least one criterion with `regression`. The parent/reviewer validates classification;
  the CLI cannot infer whether a diff actually fixes a bug. All types retain an
  independent review; scope its work instead of silently weakening the gate.

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

### Bugfix red → green

Before changing product code, write the relevant regression test and run its exact
command with repeated `--test-file relative/path` flags covering the test and its
assertion helpers. Paths are repository-relative regular files. The runner binds
their content hashes to its receipt while capturing the source-stable red run.
A meaningful baseline fails on the reported bug; an import error, missing service,
timeout or printed marker followed by an arbitrary exit is not a valid reproduction.
Inspect the raw failure, then freeze this addition on a criterion:

```json
"regression": {
  "receipt": {"path": "red/receipt.json", "sha256": "SHA256_OF_RED_RECEIPT_BYTES"},
  "exit_code": 1,
  "failure_contains": "AssertionError: reported bug persists"
}
```

The receipt path is relative to the **contract directory**, not the candidate
collection. Its hash freezes the command, baseline snapshot, raw-log hash and
captured test hashes together. Expected exit must be 1–125, with a nonblank,
assertion-specific failure signature. The checker requires a distinct stable
baseline snapshot, matching command/cwd, exact exit/signature, intact raw log and
unchanged captured test files in the current candidate. Current green evidence
must still pass its command, observations and independent review. The command may
be a test or an authorized runtime criterion. Keep baseline and candidate runs in
the same receipt-bound checkout; moving it invalidates cwd evidence.

The checker cannot infer which files contain the real assertions, whether the
failure is causally correct or whether an external service matches its observation.
The independent reviewer must verify those facts. Do not list a dummy unchanged
file while weakening a different assertion helper. If the test itself must change,
reproduce the new test on the unfixed behavior in isolation and have the parent
reconcile the new contract/baseline before continuing; never weaken a frozen test
merely to get PASS. Baseline receipt hashes and source snapshots are evidence
consistency checks, not cryptographic third-party attestations.

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
`run --test-file` additionally records `test_files: [{path, sha256}]`; a regression
baseline requires a nonempty list, whereas existing receipts remain compatible.
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
artifacts must include per-criterion verdicts and the actual commands/results inspected.
For findings record severity, `path:line`, impact, reproduction and affected criterion;
distinguish blockers from nonblocking suggestions. Verify root cause, red/green
causality, unchanged assertions, relevant regressions and runtime build provenance.
An unsupported concern is not a confirmed bug; request the smallest reproduction.
After fixes, bind the closure review to the new candidate; do not copy an old PASS.
The parent is responsible
for authenticity and adequate observations, including correct running-build
provenance. The checker cannot infer UI correctness from pixels or log prose.

## Delivery and installation

The CLI is bundled with MEGAI; receipt-owned Pi wiring installs the acceptance
skill and references without changing other harnesses or native model settings.
Existing explicit skill exclusions still win: report an unavailable gate rather
than claiming automatic activation. A repository commit does not install resources
into an already-running local Pi session; authorized update/wiring and reload are
separate operations. No host installation is implied by branch delivery.
