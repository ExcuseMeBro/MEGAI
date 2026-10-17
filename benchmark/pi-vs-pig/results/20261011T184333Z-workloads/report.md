# Pi vs PiG — Mac workload benchmark

{"pi-installed": "1.1.0", "pig-installed": "0.4.1+1.0.3", "pig-native": "0.4.1+1.0.3"}

Actual CLI, streamed protocol, file tools, shell tests and session loading. Deterministic local model, NOT real LLM coding quality.

| Case | Harness | Accept | Median ms | p90 ms | CPU ms | CPU % / core | Tree peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| text | pi-installed | 20/20 | 233.0 | 278.4 | 280.0 | 116.7 | 124.3 |
| text | pig-installed | 20/20 | 88.4 | 108.0 | 80.0 | 90.5 | 87.1 |
| text | pig-native | 20/20 | 51.6 | 73.4 | 45.0 | 79.7 | 41.3 |
| stream | pi-installed | 20/20 | 557.2 | 635.7 | 350.0 | 61.6 | 151.7 |
| stream | pig-installed | 20/20 | 414.2 | 428.2 | 125.0 | 29.9 | 90.1 |
| stream | pig-native | 20/20 | 377.7 | 409.1 | 90.0 | 23.9 | 44.1 |
| tool-cycle | pi-installed | 20/20 | 307.2 | 453.4 | 380.0 | 123.4 | 172.8 |
| tool-cycle | pig-installed | 20/20 | 157.2 | 241.9 | 160.0 | 98.8 | 111.6 |
| tool-cycle | pig-native | 20/20 | 124.3 | 166.7 | 130.0 | 99.3 | 65.8 |
| error-recovery | pi-installed | 20/20 | 276.3 | 317.8 | 350.0 | 126.4 | 162.7 |
| error-recovery | pig-installed | 20/20 | 128.0 | 145.8 | 130.0 | 100.3 | 103.9 |
| error-recovery | pig-native | 20/20 | 93.6 | 105.2 | 90.0 | 94.7 | 57.8 |
| parallel-tools | pi-installed | 20/20 | 371.4 | 413.4 | 370.0 | 100.5 | 181.1 |
| parallel-tools | pig-installed | 20/20 | 229.8 | 261.4 | 195.0 | 81.3 | 146.1 |
| parallel-tools | pig-native | 20/20 | 194.6 | 228.3 | 160.0 | 79.2 | 99.9 |
| read-large | pi-installed | 20/20 | 254.9 | 360.4 | 300.0 | 118.0 | 137.3 |
| read-large | pig-installed | 20/20 | 109.6 | 130.3 | 120.0 | 102.6 | 97.1 |
| read-large | pig-native | 20/20 | 74.2 | 88.6 | 80.0 | 106.8 | 50.8 |
| resume-2000 | pi-installed | 20/20 | 262.1 | 297.6 | 345.0 | 131.2 | 137.3 |
| resume-2000 | pig-installed | 20/20 | 176.6 | 197.5 | 200.0 | 113.1 | 114.7 |
| resume-2000 | pig-native | 20/20 | 140.1 | 164.6 | 170.0 | 117.9 | 68.6 |

## Method and limitations

live process-tree RSS sum sampled at ~5ms, shared pages may be counted more than once; short-lived peaks can be missed; excludes observer/model server

macOS time user+sys cumulative CPU; 10ms granularity. CPU% = CPU time / wall time, 100% is one core, can exceed 100%.

warm-cache installed CLI comparison, differing upstream versions; no TUI, MCP, custom extensions, live-model quality, or security isolation claims

The stream fixture deliberately sends 128 chunks 2ms apart. Read-large uses ~1.1MB text. Resume uses 2,000 user/assistant exchanges. Parallel-tools requests four 100ms bash jobs in one response; scheduling remains the harness default.

Acceptance checks exit status, valid JSONL, final stop response, exact request/tool counts, streamed deltas, edit-error signalling/recovery, returned read/parallel markers and full resumed history. Tool-cycle independently reruns four arithmetic unittest cases outside the timed region.

Fixture preparation and independent post-run acceptance are excluded from elapsed time. Process launch, provider requests, tool work, session loading and teardown are included. One warmup per harness/case; measured order is shuffled each repetition. Failed runs are retained, not dropped.

Reproduce: `python3 benchmark/pi-vs-pig/mac_workloads.py --runs 20`
