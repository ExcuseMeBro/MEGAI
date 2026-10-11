# Pi vs PiG — Mac workload benchmark

{"pi-installed": "1.1.0", "pig-installed": "0.4.1+1.0.3", "pig-native": "0.4.1+1.0.3"}

Actual CLI, streamed protocol, file tools, shell tests and session loading. Deterministic local model, NOT real LLM coding quality.

| Case | Harness | Accept | Median ms | p90 ms | CPU ms | CPU % / core | Tree peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| text | pi-installed | 10/10 | 233.3 | 239.2 | 260.0 | 111.1 | 123.8 |
| text | pig-installed | 10/10 | 127.4 | 129.8 | 80.0 | 62.8 | 86.6 |
| text | pig-native | 10/10 | 75.2 | 76.8 | 40.0 | 53.7 | 40.1 |
| stream | pi-installed | 10/10 | 552.3 | 556.1 | 325.0 | 59.2 | 151.9 |
| stream | pig-installed | 10/10 | 444.4 | 446.4 | 120.0 | 27.0 | 90.1 |
| stream | pig-native | 10/10 | 392.8 | 396.2 | 85.0 | 21.6 | 44.2 |
| tool-cycle | pi-installed | 10/10 | 316.4 | 341.0 | 360.0 | 114.9 | 171.5 |
| tool-cycle | pig-installed | 10/10 | 179.9 | 183.5 | 150.0 | 83.4 | 111.5 |
| tool-cycle | pig-native | 10/10 | 128.9 | 131.1 | 120.0 | 92.2 | 65.4 |
| error-recovery | pi-installed | 10/10 | 289.3 | 292.4 | 340.0 | 117.8 | 161.6 |
| error-recovery | pig-installed | 10/10 | 153.2 | 180.1 | 120.0 | 80.9 | 104.3 |
| error-recovery | pig-native | 10/10 | 127.7 | 130.2 | 90.0 | 69.4 | 56.9 |
| parallel-tools | pi-installed | 10/10 | 394.7 | 399.0 | 370.0 | 93.7 | 180.5 |
| parallel-tools | pig-installed | 10/10 | 233.7 | 237.2 | 180.0 | 77.7 | 145.9 |
| parallel-tools | pig-native | 10/10 | 233.6 | 236.1 | 150.0 | 64.9 | 99.9 |
| read-large | pi-installed | 10/10 | 289.4 | 292.5 | 290.0 | 100.8 | 137.0 |
| read-large | pig-installed | 10/10 | 127.2 | 130.7 | 110.0 | 88.3 | 97.3 |
| read-large | pig-native | 10/10 | 75.4 | 122.7 | 80.0 | 106.1 | 50.5 |
| resume-2000 | pi-installed | 10/10 | 286.7 | 294.0 | 335.0 | 116.8 | 137.2 |
| resume-2000 | pig-installed | 10/10 | 182.1 | 186.7 | 200.0 | 109.8 | 114.8 |
| resume-2000 | pig-native | 10/10 | 180.3 | 185.1 | 160.0 | 89.4 | 68.5 |

## Method and limitations

live process-tree RSS sum sampled at ~5ms, shared pages may be counted more than once; short-lived peaks can be missed; excludes observer/model server

macOS time user+sys cumulative CPU; 10ms granularity. CPU% = CPU time / wall time, 100% is one core, can exceed 100%.

warm-cache installed CLI comparison, differing upstream versions; no TUI, MCP, custom extensions, live-model quality, or security isolation claims

The stream fixture deliberately sends 128 chunks 2ms apart. Read-large uses ~1.1MB text. Resume uses 2,000 user/assistant exchanges. Parallel-tools requests four 100ms bash jobs in one response; scheduling remains the harness default.

Acceptance checks exit status, valid JSONL, final stop response, exact request/tool counts, streamed deltas, edit-error signalling/recovery, returned read/parallel markers and full resumed history. Tool-cycle independently reruns four arithmetic unittest cases outside the timed region.

Fixture preparation and independent post-run acceptance are excluded from elapsed time. Process launch, provider requests, tool work, session loading and teardown are included. One warmup per harness/case; measured order is shuffled each repetition. Failed runs are retained, not dropped.

Reproduce: `python3 benchmark/pi-vs-pig/mac_workloads.py --runs 10`
