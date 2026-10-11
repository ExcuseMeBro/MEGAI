# Pi vs PiG — Mac workload benchmark

{"pi-installed": "1.1.0", "pig-installed": "0.4.1+1.0.3", "pig-native": "0.4.1+1.0.3"}

Actual CLI, streamed protocol, file tools, shell tests and session loading. Deterministic local model, NOT real LLM coding quality.

| Case | Harness | Accept | Median ms | p90 ms | CPU ms | CPU % / core | Tree peak RSS MiB |
|---|---|---:|---:|---:|---:|---:|---:|
| text | pi-installed | 1/1 | 295.5 | 295.5 | 300.0 | 101.5 | 123.3 |
| text | pig-installed | 1/1 | 129.1 | 129.1 | 90.0 | 69.7 | 88.5 |
| text | pig-native | 1/1 | 73.6 | 73.6 | 60.0 | 81.5 | 41.1 |
| stream | pi-installed | 1/1 | 614.0 | 614.0 | 370.0 | 60.3 | 152.5 |
| stream | pig-installed | 1/1 | 502.0 | 502.0 | 150.0 | 29.9 | 90.2 |
| stream | pig-native | 1/1 | 446.9 | 446.9 | 100.0 | 22.4 | 44.1 |
| tool-cycle | pi-installed | 1/1 | 341.5 | 341.5 | 400.0 | 117.1 | 172.1 |
| tool-cycle | pig-installed | 1/1 | 180.7 | 180.7 | 170.0 | 94.1 | 111.5 |
| tool-cycle | pig-native | 1/1 | 173.8 | 173.8 | 130.0 | 74.8 | 65.6 |
| error-recovery | pi-installed | 1/1 | 286.9 | 286.9 | 360.0 | 125.5 | 165.1 |
| error-recovery | pig-installed | 1/1 | 184.3 | 184.3 | 140.0 | 76.0 | 104.0 |
| error-recovery | pig-native | 1/1 | 131.0 | 131.0 | 100.0 | 76.3 | 57.3 |
| parallel-tools | pi-installed | 1/1 | 398.3 | 398.3 | 400.0 | 100.4 | 180.5 |
| parallel-tools | pig-installed | 1/1 | 290.1 | 290.1 | 210.0 | 72.4 | 146.2 |
| parallel-tools | pig-native | 1/1 | 234.2 | 234.2 | 170.0 | 72.6 | 100.0 |
| read-large | pi-installed | 1/1 | 280.8 | 280.8 | 310.0 | 110.4 | 137.0 |
| read-large | pig-installed | 1/1 | 127.7 | 127.7 | 120.0 | 94.0 | 97.0 |
| read-large | pig-native | 1/1 | 125.6 | 125.6 | 80.0 | 63.7 | 51.7 |
| resume-2000 | pi-installed | 1/1 | 291.8 | 291.8 | 370.0 | 126.8 | 137.4 |
| resume-2000 | pig-installed | 1/1 | 231.9 | 231.9 | 200.0 | 86.2 | 113.9 |
| resume-2000 | pig-native | 1/1 | 179.3 | 179.3 | 180.0 | 100.4 | 70.4 |

## Method and limitations

live process-tree RSS sum sampled at ~5ms, shared pages may be counted more than once; short-lived peaks can be missed; excludes observer/model server

macOS time user+sys cumulative CPU; 10ms granularity. CPU% = CPU time / wall time, 100% is one core, can exceed 100%.

warm-cache installed CLI comparison, differing upstream versions; no TUI, MCP, custom extensions, live-model quality, or security isolation claims

The stream fixture deliberately sends 128 chunks 2ms apart. Read-large uses ~1.1MB text. Resume uses 2,000 user/assistant exchanges. Parallel-tools requests four 100ms bash jobs in one response; scheduling remains the harness default.

Acceptance checks exit status, valid JSONL, final stop response, exact request/tool counts, streamed deltas, edit-error signalling/recovery, returned read/parallel markers and full resumed history. Tool-cycle independently reruns four arithmetic unittest cases outside the timed region.

Fixture preparation and independent post-run acceptance are excluded from elapsed time. Process launch, provider requests, tool work, session loading and teardown are included. One warmup per harness/case; measured order is shuffled each repetition. Failed runs are retained, not dropped.

Reproduce: `python3 benchmark/pi-vs-pig/mac_workloads.py --runs 10`
