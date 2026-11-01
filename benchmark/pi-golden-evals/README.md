# Pi golden-eval pilot (opt-in)

This is a **disposable coding benchmark**, not an installed Pi extension, a background
observer, a substitute for Brokan acceptance, or a general production quality claim.
It tests the *incremental value of concrete failing golden-test feedback* on two
seeded defects that already pass a pinned public acceptance suite.

- Model: the selected `openai-codex/gpt-6-sol`, thinking `high`; both arms use it.
- Two fixtures: `intervals.py` and `batching.py`. Initial fixtures are identical
  within each pair. The existing independent acceptance suites are frozen at
  `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1`. Held-out golden cases check
  very large integers and are **never copied into the agent's candidate**.
- Baseline: public contract, without golden feedback. Feedback: same contract,
  plus the initial candidate's real failing golden-test output. Both get the
  same tools and identity check, in alternating order by repetition.
- After editing, the runner copies only the candidate module into separate
  evaluators with their own pinned public and golden tests. It checks scope,
  source/receipt hashes, model identity, event usage and the complete matrix.
  It retains failed runs. No self-reported test result is accepted as evidence.

The only initial fixtures are *deliberately seeded defects*. No clean control or
non-Python task is measured. This estimates detection and repair on these cases,
not a production incident rate, TNR, reviewer quality, or universal speedup. Pi
has access to the normal host permissions: the prompt's "stay in cwd" rule is
**not an OS sandbox**. Only run this with reviewed synthetic fixtures. The script
makes real model calls and consumes provider quota on explicit `matrix` invocation;
it never changes global settings, sessions, branches or installed tools.

```sh
# Run inside an isolated task checkout. Keep everything private (0700).
python3 -B -m unittest discover -s benchmark/pi-golden-evals -p 'test_runner.py' -v
python3 -B benchmark/pi-golden-evals/run.py preflight --root /private/tmp/NEW-private-preflight
python3 -B benchmark/pi-golden-evals/run.py matrix --root /private/tmp/NEW-private-matrix --repeats 2
python3 -B benchmark/pi-golden-evals/run.py verify --root /private/tmp/NEW-private-matrix
```

`matrix` and `preflight` refuse existing roots. A private matrix contains raw
prompts, Pi session JSONL, tool events, stderr, candidate files and test output:
**do not publish it**. `summary.md` is sanitized aggregate counts only; keep it
private until reviewed. Results include READY and preflight overhead; post-run
grading is common to both arms and excluded from pipeline time. Provider-reported
USD is an estimate, not an invoice. Reruns require a new root; a partial matrix
must be reported as incomplete, not filled in or silently retried.
