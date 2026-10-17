# Pi GPT-only vs DeepSeek + GPT

Fresh paired benchmark using the frozen bugfix, feature and refactor fixtures from
commit `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1`.

| Arm | Worker | Independent reviewer |
| --- | --- | --- |
| GPT-only | `openai-codex/gpt-6.1-sol`, medium | same model, fresh session, medium |
| DeepSeek + GPT | `deepseek/deepseek-flash`, high | GPT Sol, fresh session, medium |

Only a confirmed DeepSeek HTTP 402 insufficient-balance error permits one fallback
to `openai-codex/gpt-5.6-luna`, medium. Such trials are explicitly marked mixed;
a successful fallback never proves DeepSeek availability. Other errors remain failures.

```sh
python3 -B tests/pi_routing_benchmark.py
python3 -B benchmark/pi-routing/run.py matrix --root /private/new-matrix --repeats 3
python3 -B benchmark/pi-routing/run.py verify --root /private/new-matrix
# Optional, separate follow-up for review-confirmed failures (originals retained):
python3 -B benchmark/pi-routing/run.py repair --root /private/new-matrix
```

The root must be new. Keep raw prompts, model streams, sessions, candidate source
and evaluator receipts private. `summary.md` and `results.json` are summaries, not
substitutes for the raw receipts. The harness does not install or select global
settings and does not mutate Plane; the parent owns tracking and configuration.

Both arms have identical tools and resource-discovery exclusions. Native Pi READY
checks verify recorded model/thinking before task context. Each trial measures
worker planning/implementation/self-review, fresh GPT review and immutable evaluator
execution. READY calls and fallback calls are included in all-stage time/usage.
Arm order alternates between repetitions. No automatic test repair loop is used.
Acceptance tests are restored from the frozen commit in a separate evaluator;
participant edits cannot weaken them. Scope violations and reviewer failures count
against reviewed delivery even when acceptance tests pass.

This is a controlled fixture comparison, not a measurement of all production
Plane/worktree/integration overhead or a guarantee about larger tasks. Repeated
calls may benefit from provider caching. Report uncached input, output, cache read,
cache write, reasoning and provider total separately; do not add reasoning twice.
Catalog-reported USD is not actual billed cost. Incomplete or missing-usage trials
cannot pass evidence verification. Provider failures and low-quality candidates
remain in the denominator, rather than being discarded as invalid successes.

## Measured recommendation

See [results/summary.md](results/summary.md) and its sanitized trial/repair records.
The initial matrix passed acceptance 9/9 per arm, but GPT review caught two hybrid
feature defects outside the frozen tests. One repair and fresh review fixed both.
Repair-inclusive hybrid was faster and had less uncached input/reported cost, but
used more total tokens. Do not market this as universal token savings.

[recommended-roles.json](recommended-roles.json) is an explicit custom role map:
GPT Sol medium parent/planner and reviewer; DeepSeek Flash high scout/worker; Luna
5.6 medium for confirmed DeepSeek balance fallback. `routing: reviewed-hybrid`
keeps new features, ambiguous/high-risk work and trivial edits in GPT, delegates
bounded substantial low-risk bugfix/refactor work to one worker, and requires GPT
review of worker output. One repair is allowed, then unresolved findings block.
This task-family recommendation is provisional: three small fixtures are not a
representative sample of all bugfixes, features or refactors.

The role-routing extension rereads the map before each prompt but does not launch
agents or switch the parent. Install the reviewed extension and the role map only
with explicit authorization, preserving existing configuration and private backups.
For GPT parent startup, native `settings.json` must separately select
`defaultProvider: openai-codex`, `defaultModel: gpt-6.1-sol` and
`defaultThinkingLevel: medium`; the role map alone cannot set these. Per-model
levels preserve DeepSeek high and Luna 5.6 medium. No provider/auth catalog rewrite,
background service, or broad profile migration is required. Use `/reload` (or a
fresh Pi session) to load a newly installed extension; changing defaults does not
switch an already-running parent.

Local application and native startup/actual-host resource-loader receipts are in
the private MEGAI-188 evidence directory. Credentials and unrelated settings were
hash/semantic checked unchanged; host activation is separate from repository delivery.
