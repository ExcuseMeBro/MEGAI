# Pi vs PiG — Mac workload benchmark

{"pi-installed": "1.1.0", "pig-installed": "0.4.1+1.0.3", "pig-native": "0.4.1+1.0.3"}

Actual CLI, streamed protocol, file tools, shell tests and session loading. Deterministic local model, NOT real LLM coding quality.

| Case | Harness | Accept | Median ms | p90 ms | CPU ms | CPU % / core | Tree peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| text | pi-installed | 10/10 | 283.8 | 292.8 | 280.0 | 107.2 | 124.6 |
| text | pig-installed | 10/10 | 132.5 | 186.0 | 90.0 | 62.0 | 87.3 |
| text | pig-native | 10/10 | 75.1 | 76.1 | 55.0 | 73.5 | 42.1 |
| stream | pi-installed | 10/10 | 603.4 | 609.6 | 350.0 | 59.6 | 152.3 |
| stream | pig-installed | 10/10 | 446.9 | 451.3 | 130.0 | 29.2 | 90.1 |
| stream | pig-native | 10/10 | 393.2 | 396.3 | 90.0 | 22.9 | 44.4 |
| tool-cycle | pi-installed | 10/10 | 340.3 | 345.3 | 400.0 | 116.3 | 172.5 |
| tool-cycle | pig-installed | 10/10 | 184.6 | 186.9 | 170.0 | 92.0 | 111.8 |
| tool-cycle | pig-native | 10/10 | 179.0 | 182.6 | 130.0 | 77.7 | 65.9 |
| error-recovery | pi-installed | 10/10 | 294.0 | 398.9 | 360.0 | 120.0 | 164.2 |
| error-recovery | pig-installed | 10/10 | 181.5 | 183.0 | 130.0 | 72.9 | 103.6 |
| error-recovery | pig-native | 10/10 | 127.1 | 128.9 | 95.0 | 74.9 | 57.3 |
| parallel-tools | pi-installed | 10/10 | 398.4 | 454.9 | 390.0 | 95.4 | 182.1 |
| parallel-tools | pig-installed | 10/10 | 236.3 | 288.3 | 200.0 | 83.0 | 146.2 |
| parallel-tools | pig-native | 10/10 | 237.8 | 241.4 | 165.0 | 68.4 | 100.0 |
| read-large | pi-installed | 10/10 | 293.8 | 297.6 | 305.0 | 105.7 | 138.4 |
| read-large | pig-installed | 10/10 | 129.9 | 133.1 | 120.0 | 92.4 | 96.4 |
| read-large | pig-native | 10/10 | 127.5 | 130.5 | 80.0 | 64.2 | 50.7 |
| resume-2000 | pi-installed | 10/10 | 346.4 | 350.2 | 370.0 | 111.0 | 137.2 |
| resume-2000 | pig-installed | 10/10 | 183.6 | 233.9 | 210.0 | 112.4 | 114.4 |
| resume-2000 | pig-native | 10/10 | 181.0 | 185.1 | 180.0 | 96.6 | 68.7 |

## Method and limitations

live process-tree RSS sum sampled at ~5ms, shared pages may be counted more than once; short-lived peaks can be missed; excludes observer/model server

macOS time user+sys cumulative CPU; 10ms granularity. CPU% = CPU time / wall time, 100% is one core, can exceed 100%.

warm-cache installed CLI comparison, differing upstream versions; no TUI, MCP, custom extensions, live-model quality, or security isolation claims

The stream fixture deliberately sends 128 chunks 2ms apart. Read-large uses ~1.1MB text. Resume uses 2,000 user/assistant exchanges. Parallel-tools requests four 100ms bash jobs in one response; scheduling remains the harness default.

Acceptance checks exit status, valid JSONL, final stop response, exact request/tool counts, streamed deltas, edit-error signalling/recovery, returned read/parallel markers and full resumed history. Tool-cycle independently reruns four arithmetic unittest cases outside the timed region.

Fixture preparation and independent post-run acceptance are excluded from elapsed time. Process launch, provider requests, tool work, session loading and teardown are included. One warmup per harness/case; measured order is shuffled each repetition. Failed runs are retained, not dropped.

Reproduce: `python3 benchmark/pi-vs-pig/mac_workloads.py --runs 10`
