# Real-model coding benchmark on this Mac

{"pi": "1.1.0", "pig-native": "0.4.1+1.0.3"}
Model: openai-codex/gpt-6.1-sol; thinking=medium; same OAuth account.

| Task | Harness | Acceptance | Median sec | CPU ms | Tree peak RSS MiB | Output tokens |
|---|---|---:|---:|---:|---:|---:|
| query-bugfix | pi | 2/2 | 39.92 | 1210 | 164.8 | 1186 |
| query-bugfix | pig-native | 2/2 | 43.19 | 855 | 76.0 | 1208 |
| ttl-lru-feature | pi | 2/2 | 57.93 | 1540 | 172.5 | 2128 |
| ttl-lru-feature | pig-native | 2/2 | 56.90 | 1845 | 76.5 | 2116 |
| order-refactor | pi | 2/2 | 58.78 | 1620 | 175.6 | 2204 |
| order-refactor | pig-native | 2/2 | 62.45 | 1895 | 76.7 | 2204 |

Real model, actual coding/tools, 3 small Python tasks; n=2 is exploratory, not statistically decisive. System prompts/tool schemas remain harness defaults. No retry, repair, fallback or best-of selection. No browser.

Sampled live process-tree RSS sum (~5ms), includes tool children, excludes observer; shared-page duplication possible.

Provider-reported per-response token counters; no invoice/cost estimate for subscription calls.

Acceptance: independent hidden tests, intact public tests, verified model/provider, final successful stop, no timeout. Refactor also requires a changed implementation and no duplicated qty/price/discount extraction sites (AST checks). Baseline tests and all failed runs retained. No acceptance-driven second chance.

Reproduce: `python3 benchmark/pi-vs-pig/mac_live_coding.py --runs 2 --deadline 180`
