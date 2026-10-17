# Fresh Pi GPT-only vs DeepSeek + GPT

Frozen fixture commit: `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1`. Repetitions per task/arm: 3.

Both arms use native Pi, a fresh worker and independent GPT Sol medium review. GPT-only worker: GPT Sol medium. Hybrid worker: DeepSeek Flash high. Only confirmed DeepSeek 402 balance errors use Luna medium; reported separately. READY identity checks, worker, fallback, review and evaluator time are included. Global skills/extensions/context discovery is disabled equally in both arms. This measures bounded fixture execution, not full production task/Plane/worktree overhead. Reported tokens include cache; reasoning is a separate counter, not added twice. Cost is catalog-reported, not a billing receipt. Provider caching is not forced cold. No automatic repair/retry loop is used; failures are retained.

| Arm | Complete trials | Acceptance | Reviewed delivery | Fallbacks | Median seconds | Total tokens | Uncached input | Output | Cache read | Reported USD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-only | 9/9 | 9/9 | 9/9 | 0 | 86.45 | 307112 | 152820 | 12724 | 141568 | 0.447037 |
| deepseek-gpt | 9/9 | 9/9 | 7/9 | 0 | 38.93 | 401881 | 78789 | 27668 | 295424 | 0.122483 |

## Per task (median across repeats)

| Task | Arm | Seconds | Tokens | Acceptance | Reviewed delivery |
|---|---|---:|---:|---:|---:|
| bugfix | gpt-only | 74.17 | 34601 | 3/3 | 3/3 |
| bugfix | deepseek-gpt | 30.48 | 25289 | 3/3 | 3/3 |
| feature | gpt-only | 89.82 | 30642 | 3/3 | 3/3 |
| feature | deepseek-gpt | 38.93 | 30961 | 3/3 | 1/3 |
| refactor | gpt-only | 91.60 | 37545 | 3/3 | 3/3 |
| refactor | deepseek-gpt | 50.78 | 61392 | 3/3 | 3/3 |

## Separate bounded repair follow-up

Original failures above remain unchanged. Only review-confirmed failures receive one DeepSeek repair plus a fresh GPT review; all added stage cost/time is included below. No failed initial candidate is overwritten.

Repairs: 2/2. Hybrid reviewed delivery after repair: 9/9. Median end-to-end: 44.34s. Total tokens: 512395; uncached input: 100897; output: 32874; cache read: 378624; reported USD: 0.151766.
