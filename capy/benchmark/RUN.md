# Run the frozen pilot

Use one new session and clean isolated checkout per task and arm. The coordinator
supplies the full baseline commit SHA; pin that SHA rather than a moving branch.
Use Python 3.14 in both arms when available (preparation used 3.14.6 on macOS).
Report an unavailable version before starting; never silently install or substitute.
Record environment/model/usage evidence without exposing secrets. Preparation is
not participant time, and the starter's expected failures are not trial results.

## Before the clock

1. Checkout the supplied baseline into an isolated worktree or equivalent Capy
   checkout. Confirm `git status --porcelain` is empty and `git rev-parse HEAD`
   matches the supplied SHA. The coordinator owns setup; the participant owns only
   the two paths named in its prompt.
2. Verify files against `capy/benchmark/manifest.json` from the repository root:

   ```bash
   python3 - <<'PY'
   import hashlib, json
   from pathlib import Path
   manifest = json.loads(Path('capy/benchmark/manifest.json').read_text())
   for name, expected in manifest.items():
       assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
   print('PASS: frozen inputs match')
   PY
   ```

3. Confirm GPT-6 Astra/high through the host status. Pi launches require verified
   Pi harness and exact model; Capy display-only evidence is explicitly weaker.
   Supply Capy with the frozen `capy/instructions.md` before task timing. Keep
   credentials private. Preserve host/repository restrictions.
4. The coordinator retains a separate baseline copy for evaluation. Participant
   instructions/tests are public, but the evaluator never trusts modified copies.

## Send exactly one prompt

Copy the full contents, not a paraphrase, of the corresponding file into the new
session. Record submission timestamp before sending and completion timestamp when
its final result arrives. Include waits; capture the 300-second checkpoint.

- [Bugfix prompt](prompts/bugfix.md)
- [Feature prompt](prompts/feature.md)
- [Refactor prompt](prompts/refactor.md)

Run order: Pi then Capy for bugfix; Capy then Pi for feature; Pi then Capy for
refactor. No previous solutions or transcripts in new sessions. Benchmark workers
are leaves: Plane, delegation and Git delivery remain coordinator-owned.

## Capture and evaluate

Collect the complete diff, including a new `test_participant.py` if created, raw
test logs/exit statuses, model/thinking evidence, timestamps, host-reported usage
and human interventions. Do not send credentials, unrelated logs or session data.
The coordinator should retain original evidence privately and publish only the
sanitized result artifact. `git diff` alone omits untracked participant tests;
collect those separately. Never reset or clean the participant checkout to capture.

In an independent copy of the baseline, overlay only the candidate implementation.
Run the frozen acceptance suite (replace TASK with bugfix, feature or refactor):

```bash
python3 -B -m unittest discover -s capy/benchmark/cases/TASK -p 'test_acceptance.py' -v
```

Then inspect and run participant-owned tests separately in that evaluation copy.
Record acceptance and participant test counts separately; candidate tests must
not affect acceptance-suite imports or results. Check frozen non-implementation
file hashes and full scope, then run non-mutating Ruff diagnostics on changed
Python. Execute only locally reviewed candidate code in an isolated environment;
these commands are not a security sandbox.

## Preparation evidence

- Bugfix starter: 10 methods, 2 intended assertion failures, exit 1.
- Feature starter: 12 methods, 18 NotImplementedError subtest/errors, exit 1.
- Refactor starter: 10 methods, all passing, exit 0.
- Temporary positive controls: 10/12/10 passing methods. Temporary return-None
  controls fail each suite (exit 1). Control solutions are not in this checkout.
- Ruff check and format check: six fixture/test files pass.

These checks establish a usable baseline, not an exhaustive oracle or a winner.
Follow the measurement and interpretation rules in [README.md](README.md).
