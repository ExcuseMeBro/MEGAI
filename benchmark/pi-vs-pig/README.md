# Pi vs PiG: measured on this Mac

## Real-model coding results

Report: [results/20261011T185554Z-live-coding/report.md](results/20261011T185554Z-live-coding/report.md).

Same `openai-codex/gpt-6.1-sol`, `medium`, same subscription account; actual generated source and independent hidden tests. Pi 1.1.0 vs PiG 0.4.1+1.0.3 native. Two fresh runs per task/harness, randomized order, no acceptance-driven reruns or parent repairs. Normal agent iterations and tool errors are included. 180s deadline per run; zero timeouts.

| Task | Pi seconds | PiG native seconds | Pi CPU seconds | PiG CPU seconds | Pi RSS MiB | PiG RSS MiB |
|---|---:|---:|---:|---:|---:|---:|
| Query-parser bugfix | 39.92 | 43.19 | 1.210 | 0.855 | 164.8 | 76.0 |
| TTL/LRU feature | 57.93 | 56.90 | 1.540 | 1.845 | 172.5 | 76.5 |
| Order-summary refactor | 58.78 | 62.45 | 1.620 | 1.895 | 175.6 | 76.7 |

Values are medians (n=2). Each harness accepted 6/6 tasks; 188/188 independent hidden test methods passed across 12 runs. All 12 response identities explicitly reported the requested model, provider and medium thinking. Refactor also passed structural checks preventing an unchanged/duplicated implementation from being accepted. Acceptance/instrumentation checks: 6/6 passed.

**Live coding conclusion:** quality is tied within this small suite. PiG used ~54–56% less process-tree RSS, but was not consistently faster or lower-CPU. Total elapsed across six runs: Pi 313.26s, PiG 325.08s. Total measured CPU: Pi 8.74s, PiG 9.19s. Model latency, stochastic outputs, network and provider prompt caching are uncontrolled; n=2 is exploratory and does not establish a general winner. Subscription quota was used; no monetary invoice estimate is available.

Reproduce: `python3 benchmark/pi-vs-pig/mac_live_coding.py --runs 2 --deadline 180`.

## Controlled harness evidence

- Machine: MacBookPro18,2, Apple Silicon arm64, 64 GiB, 10 logical CPUs, macOS 27.0.1.
- Pi 1.1.0; PiG 0.4.1+1.0.3. Different upstream versions: not an equal-version parity experiment.
- Final workload report: [results/20261011T184333Z-workloads/report.md](results/20261011T184333Z-workloads/report.md).
- Startup baseline: [results/20261011T183718Z/report.md](results/20261011T183718Z/report.md).
- Final workload acceptance: 420/420 measured runs passed (7 cases × 3 command variants × 20 repetitions). Warmups are excluded.
- Focused instrumentation/fixture checks: 3/3 passed.
- No paid API calls. A deterministic loopback SSE model drives the **actual installed CLI, actual tools, real fixture edits and real shell assertions**. This does not measure real LLM coding quality.

## Median elapsed time (ms)

| Case | Pi command | PiG command (npm launcher) | PiG native | Native speedup vs Pi |
|---|---:|---:|---:|---:|
| One reply | 233.0 | 88.4 | 51.6 | 4.51× |
| Stream, 128 delayed chunks | 557.2 | 414.2 | 377.7 | 1.48× |
| Read → edit → write → unittest | 307.2 | 157.2 | 124.3 | 2.47× |
| Failed edit → recovery → assertion | 276.3 | 128.0 | 93.6 | 2.95× |
| Four 100ms bash jobs | 371.4 | 229.8 | 194.6 | 1.91× |
| Read ~1.1MB file | 254.9 | 109.6 | 74.2 | 3.43× |
| Resume 2,000 exchanges | 262.1 | 176.6 | 140.1 | 1.87× |

## Tool-cycle CPU / memory

| Variant | CPU time ms | Average CPU / one core | Median process-tree peak RSS MiB | Acceptance |
|---|---:|---:|---:|---:|
| Pi | 380 | 123.4% | 172.8 | 20/20 |
| PiG npm launcher | 160 | 98.8% | 111.6 | 20/20 |
| PiG native | 130 | 99.3% | 65.8 | 20/20 |

All cases' CPU, RSS, p90, first-request timing and individual acceptance evidence are in the final report and JSON files. RSS is the sampled sum of live process-tree resident memory, not physical unique memory or JS/Go heap. Shared pages can be counted twice and short peaks can be missed. The observer and test-model server are excluded. CPU time is cumulative user+system from macOS `time`, with 10ms granularity. Percentages are medians of per-run ratios; they are not ratios of table medians.

## Reproduce

```sh
python3 -m unittest discover -s benchmark/pi-vs-pig -p 'test_*.py' -v
python3 benchmark/pi-vs-pig/mac_baseline.py
python3 benchmark/pi-vs-pig/mac_workloads.py --runs 20
```

Uses temporary fixture directories and fresh agent configuration. Does not read user provider credentials, alter user settings, or change project source. Workload setup and independent acceptance tests are outside elapsed time. Process startup, requests, streaming, tools, session resume and teardown are inside it. One warmup per workload/variant; randomized interleaving; filesystem caches are warm. Normal desktop activity is uncontrolled and contributes noise.

Earlier `*-smoke` and workload directories are exploratory evidence, **not final results**. Their timing included Python timeout-wait polling (up to 50ms latency). The final run uses blocking process wait plus a separate watchdog. Do not pool those runs with the final data.

## Conclusion / limits

On these controlled workloads PiG is faster and consumes less CPU time and RSS than Pi. Native PiG avoids its npm Node launcher's overhead. Real coding tasks can be dominated by model latency and can fail because of model behavior or compatibility differences; these measurements do not establish coding-quality superiority. TUI, MCP, custom extensions, real-provider authentication, compaction, sustained multi-agent concurrency and real-model task acceptance remain unmeasured.
