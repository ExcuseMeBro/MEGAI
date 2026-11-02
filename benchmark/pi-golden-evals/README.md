# Pi golden-eval pilot (opt-in)

This is a **disposable coding benchmark**, not an installed Pi extension, a background
observer, a substitute for Brokan acceptance, or a general production quality claim.
It tests the *incremental value of independent golden-test feedback* on seeded
defects and the risk of unnecessary edits to clean control implementations.

- Model: the selected `openai-codex/gpt-6-sol`, thinking `high`; both arms use it.
- Original `pilot` cohort: `intervals.py` and `batching.py`, unchanged, with
  existing independent acceptance suites frozen at
  `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1`. Original pilot evidence
  remains historical and is not reinterpreted as this expanded cohort.
- `validation` cohort: new seeded `query.py` malformed-encoding defect and two
  clean controls (`intervals-clean`, `batching-clean`). All initially pass their
  public-contract acceptance tests; query fails held-out golden tests while both
  clean controls pass. Initial fixtures are identical within each matched pair.
  New source/test/contract SHA256 values are pinned in each private run manifest.
  Held-out tests are **never copied into an agent's candidate**.
- Baseline: public contract without golden feedback. Feedback: same contract,
  plus the initial candidate's independent result (real failure output for
  defects, green confirmation for clean controls). Both arms get identical
  starting source, model, thinking, tools and identity check, in alternating
  order by repetition. A clean control passes only when left unchanged with
  no extra files; a defect passes only when fixed without regressions.
- After editing, the runner copies only the candidate module into separate
  evaluators with their own pinned public and golden tests. It checks scope,
  source/receipt hashes, model identity, event usage and the complete matrix.
  It retains failed runs. No self-reported test result is accepted as evidence.

Clean-control over-edit is only a proxy for false positives, **not a production
TNR**; even a green candidate may have untested bugs. The new defect is synthetic,
not sampled from production incidents. There is no blinded reviewer check, no
non-Python task, and no claim about production incident rates or universal speedup. Pi
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

# New cohort; keep its results separate from the original pilot.
python3 -B benchmark/pi-golden-evals/run.py preflight --cohort validation --root /private/tmp/NEW-control-preflight
python3 -B benchmark/pi-golden-evals/run.py matrix --cohort validation --root /private/tmp/NEW-control-matrix --repeats 2
python3 -B benchmark/pi-golden-evals/run.py verify --root /private/tmp/NEW-control-matrix
```

`matrix` and `preflight` refuse existing roots. A private matrix contains raw
prompts, Pi session JSONL, tool events, stderr, candidate files and test output:
**do not publish it**. `summary.md` is sanitized aggregate counts only; keep it
private until reviewed. Results include READY and preflight overhead; post-run
grading is common to both arms and excluded from pipeline time. Provider-reported
USD is an estimate, not an invoice. Reruns require a new root; a partial matrix
must be reported as incomplete, not filled in or silently retried.
