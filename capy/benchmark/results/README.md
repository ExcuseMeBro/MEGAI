# Pilot evidence

[Pi bugfix result](pi-bugfix.json) is one completed trial against baseline
`04c0bf4105d1734fecff2884446e227fd918fb0d`. Capy has not been evaluated yet; there is
no comparative winner. Remaining tasks are not silently counted as failures or
successes. Execution status stays in the linked Plane item.

Pi + MEGAI, verified GPT-6 Astra/high: 10/10 frozen acceptance methods and one
participant regression method passed in a separate evaluation copy. Parent review
found no issue; it was not blind or an independent model review. Scope and frozen
input hashes passed. Evaluator Ruff lint/format both passed on the two changed
Python files. Raw passing test outputs are retained alongside the JSON.

Task duration is 89.646 seconds from native Pi task-entry timestamp through final
assistant-entry timestamp, including tool/model waits. The worker's 72-second
figure excludes arrival-to-first-tool and final-response latency and is therefore
not the benchmark's end-to-end task metric. READY/setup usage is excluded.

Usage counters are summed across 13 task model requests, not unique context size:
25,941 uncached input, 145,792 cached input and 1,625 output tokens. Native runtime
pricing estimates $0.486452; this is **not verified billing**. Actual charged cost
is unknown. Counter semantics may differ from Capy and must be reconciled before
cost comparison. No human repair prompts were sent.

The candidate diff and regression file remain privately retained in the stopped
worker's isolated checkout and evaluator evidence directory. They are not merged
into the starter or published here before the other arm runs. Use the pinned
baseline, not the latest `capy` head, for every subsequent trial.
