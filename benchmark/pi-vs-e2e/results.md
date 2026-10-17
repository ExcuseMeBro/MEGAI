# Pi vs Pi + e2e: local browser pilot

Measured 2026-10-03 on macOS arm64. Same GPT-6.1-Sol, requested high thinking, headless Chromium, 1280×720. One frozen login -> create project -> verify flow, three trials per arm. All 12 passed independent persisted-state acceptance.

## Results

| Arm | Mean wall time | Median wall time | Mean total tokens | Pi tokens | e2e tokens | Cached input tokens | Pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| pi-live | 25.44s | 25.46s | 6,098 | 6,098 | 0 | 341 | 3/3 |
| e2e-cold | 46.06s | 46.28s | 34,985 | 1,823 | 33,162 | 12,843 | 3/3 |
| e2e-warm | 15.65s | 15.76s | 1,763 | 1,763 | 0 | 0 | 3/3 |
| pi-saved | 11.11s | 11.13s | 1,501 | 1,501 | 0 | 0 | 3/3 |

`Total tokens` includes prompt-cache reads, not just uncached input. e2e input already includes its cached portion; Pi reports that portion separately. The two sources are normalized without double-counting. Every completed Pi assistant message is counted once. Nested e2e totals are reconciled with each native SDK response receipt, not inferred from Pi shell output.

## Interpretation

- Cold e2e used 5.74× the tokens and 1.81× the time of live Pi + Playwright. It made eight nested model calls per trial; live Pi made five, six and five calls and batched form actions.
- Warm e2e reduced total tokens by 71.1% and wall time by 38.5% versus live Pi. All three warm runs replayed seven actions with zero nested model calls. Pi still made two calls to launch and summarize the test.
- The saved Playwright control was cheaper and faster than warm e2e. Replay is not unique to e2e; deterministic tests need no model at all when run directly in CI. Those CI-only runs were not timed in this pilot.
- For this stable flow, e2e is not a first-run token/speed optimization. Its reason to adopt would be natural-language test authoring and recovery when UI changes; recovery and UI churn were not measured here.

## Individual trials

| Trial | Wall time | Pi tokens | e2e tokens | Total tokens | Prompt-cache reads |
| --- | ---: | ---: | ---: | ---: | ---: |
| pi-live-1 | 22.68s | 5,596 | 0 | 5,596 | 0 |
| e2e-cold-1 | 46.28s | 1,824 | 33,164 | 34,988 | 17,792 |
| e2e-warm-1 | 15.37s | 1,763 | 0 | 1,763 | 0 |
| pi-saved-1 | 11.13s | 1,501 | 0 | 1,501 | 0 |
| e2e-cold-2 | 47.51s | 1,826 | 33,161 | 34,987 | 9,216 |
| e2e-warm-2 | 15.82s | 1,762 | 0 | 1,762 | 0 |
| pi-saved-2 | 10.54s | 1,501 | 0 | 1,501 | 0 |
| pi-live-2 | 28.18s | 7,095 | 0 | 7,095 | 1,024 |
| pi-live-3 | 25.46s | 5,603 | 0 | 5,603 | 0 |
| e2e-cold-3 | 44.40s | 1,819 | 33,161 | 34,980 | 11,520 |
| e2e-warm-3 | 15.76s | 1,763 | 0 | 1,763 | 0 |
| pi-saved-3 | 11.65s | 1,501 | 0 | 1,501 | 0 |

## Scope and limitations

- This is an execution microbenchmark, not an app-development or full global-MEGAI-profile benchmark. Pi core uses the same native model/auth with bash only; context files, extensions, skills, templates and themes are disabled in both arms for the child process only. Global configuration is untouched.
- Live Pi sees full accessible Playwright snapshots and can batch actions; e2e uses its built-in observation/action loop. Tool topology and policies differ by design. This does not isolate an intrinsic harness efficiency difference.
- The e2e and saved-Playwright tests, fixture, and direct browser bridge were prepared before timing. No test-authoring or package-install cost is included in the trial table. Cold means empty e2e action-replay cache, not an empty provider prompt cache.
- Fresh fixture state, cookies and browser instances per trial. Each cold/warm pair shares only that pair’s action recording. Runs were sequential and first-arm order alternated; provider cache state and service latency were not controlled.
- Native e2e requests were audited as GPT-6.1-Sol with reasoning.effort=high. The SDK needs forceReasoning=true for this model ID. Both providers reported zero reasoning tokens on these trivial tasks; requested effort is not a claim that hidden reasoning occurred.
- Small synthetic flow, n=3 per arm. No significance, production reliability, billing, security, mobile, visual design, or large-app claim.
- Initial preparation had an output-path validation failure, a report-envelope parser error after a passed default-reasoning run, and an audit-parser error after one native response. These were not trials and were not silently rerun into the table. All raw setup evidence is retained; the audit-parser failure’s provider usage was lost by that failed wrapper, so setup token expenditure is not claimed exact.
- The measured 12-trial matrix consumed 133,040 provider-reported tokens. Parent preparation/research conversation and preflight tokens are additional and excluded; this is not the total cost of doing the investigation.

## Evidence

`results.json` contains sanitized trial records, source checksums and raw-receipt SHA-256 hashes. Raw Pi JSONL, e2e reports, SDK request metadata/usage, frozen prompts and the exact measured source snapshot are retained privately outside Git. The original measured runner is preserved even though the delivered version separates metrics and namespaces replay paths for safe reruns.

See `README.md` for reproduction and the Plane work item AS4DABD7BE-185 for the evidence location and delivery receipt.
