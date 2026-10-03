# Pi vs Pi + e2e

Execution pilot for `tester-army/e2e`, requested in Plane **AS4DABD7BE-185**.
Results: [results.md](results.md), machine-readable [results.json](results.json).

## Frozen task and arms

Local scriptless HTML fixture: sign in as the explicitly fictitious
`bench@example.test` / `demo-password`, create `Bench Project` with description
`Token and speed benchmark`, and verify the project heading and success status.
The parent independently checks one correct login, one correct project and event
order. Every trial has fresh server state, cookies and browser context.

| Arm | Behavior |
| --- | --- |
| `pi-live` | Native Pi observes Playwright accessible snapshots and decides actions through the browser bridge; it may batch commands. |
| `e2e-cold` | Native Pi runs the frozen e2e test; its built-in agent acts with an empty action-replay cache. |
| `e2e-warm` | Native Pi runs the same test against fresh app state using that cold trial's verified recording. |
| `pi-saved` | Native Pi runs a frozen deterministic Playwright script, a control for the benefit of saving actions. |

Three sequential trials per arm, cold before warm in each pair. First-arm order
alternates. Native Pi `1.0.0`, e2e `0.16.0`, web engine `0.11.2`, Playwright
`1.63.0`, AI SDK `7.0.127`, OpenAI SDK `4.0.83`, Node `24.18.0`.
The lockfile pins installation. Both model paths select GPT-6.1-Sol, high thinking.

Pi is a controlled **core-only child invocation**, not the complete global MEGAI
profile: bash only, no extensions, skills, context files, templates or themes.
These flags affect child processes, not saved user settings. The same controls
apply to every arm. Bash and the bridge are not a security sandbox.

## Measure

- Monotonic wall clock around the full Pi CLI process, including startup, all
  model/tool waits, nested e2e startup and shutdown. Fixture provisioning and
  post-run acceptance are outside the interval; browser launch is inside it.
- Sum only completed Pi assistant-message usage, never streaming snapshots or
  duplicate turn events. Inspect error/aborted stop reasons as well as exit codes.
- Sum e2e report step model totals, including failed attempts if any. Reconcile
  nested totals with native AI SDK request/response metadata. Never mistake
  e2e model usage for free just because Pi launched it through bash.
- Pi separates cache reads from uncached input. e2e input includes cache reads.
  `metrics.mjs` normalizes totals and checks authoritative counters.
- Native request metadata confirms e2e model and `reasoning.effort=high`.
  `forceReasoning=true` is needed because this model ID is not recognized as a
  reasoning model by the installed OpenAI SDK. The wrapper observes the native
  result; it does not proxy or rewrite requests, tools or credentials.
- Fresh cache namespaces per evidence root, empty cold recordings, seven replayed
  actions and zero nested warm calls are required. Failures stop the matrix rather
  than becoming hidden retries. A trial directory cannot be overwritten.

This is **execution only**: all scripts were prepared before timing. Authoring,
installation, this parent conversation and preparation/preflight are excluded from
the table. Initial setup failures and one lost preflight usage receipt are disclosed
in the results. There is no exact all-in setup-token claim or verified billing claim.

## Reproduce

Requires Node 24+, native `pi` on PATH and an existing native ChatGPT OAuth login
with GPT-6.1-Sol available. Model/provider/thinking are deliberately fixed; no
fallback is permitted. Run only with explicit permission to consume that account's
model allowance. Credentials are copied into a child-only supported
`E2E_OAUTH_CREDENTIALS` environment variable, not written to an e2e auth file.
The runner refuses a credential with less than one hour remaining; it does not
sign in or refresh on the user's behalf.

```sh
cd benchmark/pi-vs-e2e
npm ci --ignore-scripts --no-audit --no-fund
./node_modules/.bin/playwright install chromium
node --test tests/*.test.mjs

# Unique PRIVATE is required for every experiment, outside source control.
PRIVATE="$HOME/.megai/benchmarks/pi-e2e-$(date +%s)"
node bench.mjs preflight "$PRIVATE"
node bench.mjs run "$PRIVATE"
node summarize.mjs "$PRIVATE"
```

`preflight` makes native model calls but is excluded from comparisons. `run` makes
12 timed Pi invocations; use a new private directory instead of replaying an
incomplete matrix. Deadlines are 300 seconds per Pi invocation and 240 seconds per
e2e attempt, no e2e retries. No daemon remains running after completion.
`summary` generation rechecks all 12 trials, counters, receipts and replay states.

e2e restricts output/cache paths to its project root, so `.evidence/` temporarily
holds its artifacts and recordings. These are ignored by Git and copied to the
private evidence root. Preserve that copy before retiring a worktree. Native Pi
JSONL, prompts, exact measured source and source checksums also live privately.
Only sanitized results and receipt hashes are committed. No global Pi/e2e
configuration changes, main promotion or push are part of this benchmark.

## Focused verification

`node --test tests/*.test.mjs` tests accounting, model identity, missing counters,
pure replay and fixture authentication/state isolation without launching a browser.
The actual benchmark matrix supplies browser runtime evidence. Review does not
start another browser automatically.

## Primary references

- [Repository README](https://github.com/tester-army/e2e#readme)
- [Subscriptions](https://e2e.tester.army/docs/subscriptions)
- [Action replay](https://e2e.tester.army/docs/cache)
- [Configuration](https://e2e.tester.army/docs/reference/config)
- [Reporters and step models](https://e2e.tester.army/docs/reference/reporters)
- Installed Pi `docs/cli.md`, `docs/cli-integration.md`, `docs/json.md`, `docs/models.md`.
