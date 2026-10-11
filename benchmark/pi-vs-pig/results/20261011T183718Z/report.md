# Pi vs PiG — local Mac baseline

Installed versions: pi-installed: 1.1.0, pig-installed: 0.4.1+1.0.3, pig-native: 0.4.1+1.0.3

30 interleaved runs per case, 3 warmups; no paid API calls. Different upstream versions; this is not an equal-version parity comparison.

| Harness | Case | Median ms | p90 ms | CPU ms | Max-process RSS MiB |
|---|---|---:|---:|---:|---:|
| pi-installed | version | 173.0 | 178.1 | 190.0 | 115.6 |
| pi-installed | help | 231.3 | 240.3 | 290.0 | 125.9 |
| pig-installed | version | 55.9 | 57.9 | 40.0 | 46.1 |
| pig-installed | help | 95.9 | 104.5 | 100.0 | 46.0 |
| pig-native | version | 19.2 | 19.7 | 0.0 | 26.8 |
| pig-native | help | 59.5 | 68.0 | 60.0 | 39.7 |

RSS is NOT total process-tree memory. Wall time includes the time wrapper and process startup. Warm-cache startup does not establish coding speed, task quality, or cold-boot performance.

Reproduce: `python3 benchmark/pi-vs-pig/mac_baseline.py`
