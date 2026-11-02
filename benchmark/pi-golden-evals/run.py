#!/usr/bin/env python3
"""Optional, bounded Pi golden-eval pilot; never changes installed Pi or Brokan acceptance.

Runs only on disposable Python fixtures. Provider calls consume quota when `matrix`
is explicitly invoked. Raw model events/prompts remain under a private (0700) root.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import statistics
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIXTURE_COMMIT = "095a664e7fb8519a69e0bff9f0b1d452c26e4cf1"
MODEL = "openai-codex/gpt-6-sol"
THINKING = "high"
CASES = {"intervals": "bugfix", "batching": "feature"}  # frozen pilot contract
COHORTS = {"pilot": tuple(CASES),
           "validation": ("query", "intervals-clean", "batching-clean")}
ARMS = ("baseline", "golden-feedback")
TIMEOUT = 180


def clean(case: str) -> bool:
    return case.endswith("-clean")


def module_name(case: str) -> str:
    return f"{case.removesuffix('-clean')}.py"


def seed(case: str) -> Path:
    return HERE / ("fixtures-clean" if clean(case) else "fixtures") / module_name(case)


def golden(case: str) -> bytes:
    return (HERE / "golden" / module_name(case)).read_bytes()


def contract(case: str) -> bytes:
    if case in ("query", "intervals-clean", "batching-clean"):
        return (HERE / "contracts" / ("clean.md" if clean(case) else "query.md")).read_bytes()
    return subprocess.run(["git", "-C", str(REPO), "show", f"{FIXTURE_COMMIT}:capy/benchmark/tasks.md"],
                          capture_output=True, check=True).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def frozen(case: str) -> bytes:
    if case == "query":
        return (HERE / "acceptance" / "query.py").read_bytes()
    path = f"capy/benchmark/cases/{CASES[case.removesuffix('-clean')]}/test_acceptance.py"
    return subprocess.run(["git", "-C", str(REPO), "show", f"{FIXTURE_COMMIT}:{path}"],
                          capture_output=True, check=True).stdout


def check(candidate: Path, test: bytes, directory: Path) -> dict:
    """Execute immutable parent-owned tests on a copy, not the candidate's tests."""
    directory.mkdir()
    (directory / "test_acceptance.py").write_bytes(test)
    (directory / candidate.name).write_bytes(candidate.read_bytes())
    started = time.monotonic()
    try:
        result = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", ".",
                                 "-p", "test_acceptance.py", "-v"], cwd=directory,
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                                     "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
                                     "HOME": str(directory)}, capture_output=True, text=True, timeout=20)
        output, code = result.stdout + result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        output, code = "EVALUATOR TIMEOUT (20s): " + str(error), None
    (directory / "output.txt").write_text(output)
    count = re.search(r"Ran (\d+) tests?", output)
    receipt = {"passed": code == 0 and count is not None and int(count.group(1)) > 0,
               "exit": code, "tests": int(count.group(1)) if count else 0,
               "seconds": time.monotonic() - started, "module_sha256": sha(candidate.read_bytes()),
               "test_sha256": sha(test), "output_sha256": sha(output.encode())}
    save(directory / "receipt.json", receipt)
    return receipt


def events(text: str) -> dict:
    usage = {key: 0 for key in ("input", "output", "cache_read", "cache_write", "total")}
    usage["cost_usd"] = 0.0
    models, stops, errors, final = set(), [], [], ""
    complete, requests = True, 0
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "message_end" or event.get("message", {}).get("role") != "assistant":
            continue
        message = event["message"]
        requests += 1
        models.add(f"{message.get('provider')}/{message.get('model')}")
        stops.append(message.get("stopReason"))
        if message.get("stopReason") in ("error", "aborted"):
            errors.append(message.get("errorMessage") or message.get("stopReason"))
        final = "\n".join(block.get("text", "") for block in message.get("content", [])
                          if block.get("type") == "text")
        counters = message.get("usage")
        if not isinstance(counters, dict) or "totalTokens" not in counters:
            complete = False
            continue
        for name, field in (("input", "input"), ("output", "output"),
                            ("cache_read", "cacheRead"), ("cache_write", "cacheWrite"),
                            ("total", "totalTokens")):
            usage[name] += counters.get(field) or 0
        usage["cost_usd"] += (counters.get("cost") or {}).get("total") or 0
    return {"usage": usage, "models": sorted(models), "stops": stops, "errors": errors,
            "complete_usage": complete and requests > 0, "requests": requests, "final": final}


def identity(session_dir: Path) -> bool:
    files = list(session_dir.glob("*.jsonl"))
    if len(files) != 1:
        return False
    selected = level = None
    for line in files[0].read_text().splitlines():
        entry = json.loads(line)
        if entry.get("type") == "model_change":
            selected = f"{entry.get('provider')}/{entry.get('modelId')}"
        if entry.get("type") == "thinking_level_change":
            level = entry.get("thinkingLevel")
    return selected == MODEL and level == THINKING


def invoke(cwd: Path, directory: Path, session_dir: Path, prompt: str, tools: bool,
           resume: bool = False) -> dict:
    directory.mkdir()
    (directory / "prompt.txt").write_text(prompt)
    cmd = ["pi", "-p", "--mode", "json", "--no-extensions", "--no-skills",
           "--no-context-files", "--no-prompt-templates", "--no-themes", "--no-approve",
           "--offline", "--model", MODEL, "--thinking", THINKING,
           "--session-dir", str(session_dir)]
    cmd += ["--tools", "read,bash,edit,write"] if tools else ["--no-tools"]
    if resume:
        cmd += ["--session", str(next(session_dir.glob("*.jsonl")))]
    cmd.append(prompt)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key in ("PI_SESSION_ID", "PI_SESSION_FILE", "PI_PROVIDER", "PI_MODEL", "PI_REASONING_LEVEL"):
        env.pop(key, None)
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = proc.communicate(timeout=TIMEOUT)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        # Only the process group created above for this benchmark trial is signalled.
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        exit_code = None
        stderr += f"\nBENCHMARK TIMEOUT ({TIMEOUT}s)\n"
    (directory / "events.jsonl").write_text(stdout)
    (directory / "stderr.txt").write_text(stderr)
    receipt = events(stdout)
    receipt.update({"seconds": time.monotonic() - started, "exit": exit_code,
                    "identity_ok": identity(session_dir), "prompt_sha256": sha(prompt.encode())})
    save(directory / "receipt.json", receipt)
    return receipt


def stage_ok(stage: dict) -> bool:
    return (stage["exit"] == 0 and stage["identity_ok"] and stage["models"] == [MODEL]
            and stage["complete_usage"] and stage["stops"] and stage["stops"][-1] == "stop"
            and not stage["errors"])


def extra_paths(candidate: Path, module: Path) -> list[str]:
    return sorted(str(p.relative_to(candidate)) for p in candidate.rglob("*")
                  if p != module and (p.is_file() or p.is_symlink()))


def trial(root: Path, case: str, arm: str, repetition: int, spec: str) -> dict:
    directory = root / f"r{repetition}-{case}-{arm}"
    directory.mkdir()
    candidate = directory / "candidate"
    candidate.mkdir()
    module = candidate / module_name(case)
    initial = seed(case).read_bytes()
    module.write_bytes(initial)
    test = frozen(case)
    held_out = golden(case)
    started = time.monotonic()
    feedback = ""
    preflight = None
    if arm == "golden-feedback":
        preflight = check(module, held_out, directory / "preflight")
        feedback = (directory / "preflight" / "output.txt").read_text()[-6000:]
    sessions = directory / "sessions"
    sessions.mkdir()
    ready = invoke(candidate, directory / "ready", sessions,
                   "Reply exactly READY. Do not use tools or inspect files.", False)
    work = None
    if stage_ok(ready) and ready["final"].strip() == "READY":
        prompt = (
            "You are a bounded Pi coding benchmark worker on disposable fixtures. Do not delegate, "
            "commit, install, use network, open a browser, read other trials, or access paths outside cwd. "
            f"Only modify {module.name}; do not edit tests. The public contract follows. "
            "Find and fix any defects, add no dependencies. Final response: changed file and actual checks "
            "(never claim a check you did not run).\n\n" + spec + "\n\n"
            + (("Independent golden evaluator on THIS starting candidate: "
                + ("PASS (all held-out checks pass). Do not change correct code without evidence."
                   if preflight["passed"] else "FAIL (fix the source, not the test):\n" + feedback))
               if arm == "golden-feedback" else
               "No additional evaluator feedback is available. Recheck the contract independently.")
        )
        work = invoke(candidate, directory / "work", sessions, prompt, True, True)
    if module.is_symlink() or not module.is_file():
        raise RuntimeError("candidate module missing or symlinked; retain partial matrix")
    final_frozen = check(module, test, directory / "final-frozen")
    final_golden = check(module, held_out, directory / "final-golden")
    changes = extra_paths(candidate, module)
    changed = module.read_bytes() != initial
    scope = not changes and not module.is_symlink() and (not changed if clean(case) else changed)
    passed = bool(work and stage_ok(work) and final_frozen["passed"] and final_golden["passed"] and scope)
    row = {"case": case, "kind": "clean" if clean(case) else "defect",
           "changed": changed, "arm": arm, "repeat": repetition, "model": MODEL, "thinking": THINKING,
           "initial_sha256": sha(initial), "candidate_sha256": sha(module.read_bytes()),
           "preflight": preflight, "frozen": final_frozen, "golden": final_golden,
           "scope_ok": scope, "unexpected_files": changes, "pass_trial": passed,
           "pipeline_seconds": time.monotonic() - started - final_frozen["seconds"] - final_golden["seconds"],
           "usage": {key: ready["usage"][key] + (work["usage"][key] if work else 0)
                     for key in ready["usage"]},
           "complete_usage": bool(work and ready["complete_usage"] and work["complete_usage"])}
    save(directory / "result.json", row)
    print(json.dumps({key: row[key] for key in ("case", "arm", "repeat", "pass_trial", "pipeline_seconds", "usage")}), flush=True)
    return row


def source_hashes(case: str) -> dict[str, str]:
    return {name: sha(data) for name, data in (("seed", seed(case).read_bytes()),
            ("frozen", frozen(case)), ("golden", golden(case)), ("contract", contract(case)))}


def verify(root: Path, repeats: int) -> list[dict]:
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["runner_sha256"] == sha(Path(__file__).read_bytes()), "runner changed"
    assert manifest["model"] == MODEL and manifest["thinking"] == THINKING
    cohort = manifest["cohort"]
    assert cohort in COHORTS and manifest["cases"] == list(COHORTS[cohort])
    assert manifest["sources"] == {case: source_hashes(case) for case in COHORTS[cohort]}, "source drift"
    rows = [json.loads(p.read_text()) for p in sorted(root.glob("r*-*/result.json"))]
    expected = {(case, arm, r) for r in range(1, repeats + 1) for case in COHORTS[cohort] for arm in ARMS}
    assert len(rows) == len(expected) and {(x["case"], x["arm"], x["repeat"]) for x in rows} == expected, "incomplete or duplicate matrix"
    assert manifest["fixture_commit"] == FIXTURE_COMMIT
    for row in rows:
        case = row["case"]
        assert case in COHORTS[cohort] and row["arm"] in ARMS and isinstance(row["repeat"], int)
        assert row["kind"] == ("clean" if clean(case) else "defect")
        directory = root / f"r{row['repeat']}-{case}-{row['arm']}"
        candidate = directory / "candidate" / module_name(case)
        assert not candidate.is_symlink(), "symlinked candidate"
        assert sha(candidate.read_bytes()) == row["candidate_sha256"], "candidate drift"
        assert sha(seed(case).read_bytes()) == row["initial_sha256"], "fixture drift"
        changes = extra_paths(candidate.parent, candidate)
        assert row["unexpected_files"] == changes, "scope inventory drift"
        changed = row["candidate_sha256"] != row["initial_sha256"]
        assert row["changed"] == changed
        assert row["scope_ok"] == (not changes and (not changed if clean(case) else changed)), "scope verdict drift"
        for field, relative, test in (("frozen", "final-frozen", frozen(case)),
                                      ("golden", "final-golden", golden(case))):
            receipt = json.loads((directory / relative / "receipt.json").read_text())
            assert receipt == row[field] and receipt["module_sha256"] == row["candidate_sha256"]
            assert receipt["test_sha256"] == sha(test) and receipt["tests"] > 0
            assert receipt["output_sha256"] == sha((directory / relative / "output.txt").read_bytes())
            assert (receipt["passed"] == (receipt["exit"] == 0)), "verdict drift"
            with tempfile.TemporaryDirectory(prefix="verify-", dir=root) as scratch:
                fresh = check(candidate, test, Path(scratch) / "grade")
                for key in ("passed", "exit", "tests", "module_sha256", "test_sha256"):
                    assert fresh[key] == receipt[key], "source-current evaluator drift"
        if row["arm"] == "golden-feedback":
            receipt = json.loads((directory / "preflight" / "receipt.json").read_text())
            assert receipt == row["preflight"] and receipt["passed"] == clean(case)
            assert receipt["module_sha256"] == row["initial_sha256"]
            assert receipt["test_sha256"] == sha(golden(case))
            assert receipt["output_sha256"] == sha((directory / "preflight" / "output.txt").read_bytes())
        else:
            assert row["preflight"] is None
        stages = []
        for phase in ("ready", "work"):
            path = directory / phase / "receipt.json"
            if not path.exists():
                continue
            stage = json.loads(path.read_text())
            parsed = events((directory / phase / "events.jsonl").read_text())
            for key in ("usage", "models", "stops", "errors", "complete_usage", "requests", "final"):
                assert stage[key] == parsed[key], "event evidence drift"
            assert stage["prompt_sha256"] == sha((directory / phase / "prompt.txt").read_bytes())
            assert identity(directory / "sessions") == stage["identity_ok"]
            stages.append(stage)
        assert len(stages) == 2 and row["complete_usage"] == all(s["complete_usage"] for s in stages)
        assert row["usage"] == {key: sum(stage["usage"][key] for stage in stages) for key in stages[0]["usage"]}
        assert row["pass_trial"] == bool(stage_ok(stages[1]) and row["frozen"]["passed"]
                                         and row["golden"]["passed"] and row["scope_ok"])
        assert row["pipeline_seconds"] >= sum(s["seconds"] for s in stages)
    return rows


def summarize(root: Path, rows: list[dict], repeats: int, cohort: str) -> None:
    cases = COHORTS[cohort]
    lines = [f"# Pi golden-eval {cohort} cohort: matched real-model runs", "",
             f"Model {MODEL}, thinking {THINKING}, repeats {repeats}; identical candidate within "
             "each pair, arms alternate order. Pilot frozen tests are from " + FIXTURE_COMMIT + ".",
             "Both arms get the same public contract, tools and READY check. Feedback arm also gets the "
             "initial independent held-out result: failure output for defects, PASS notice for clean controls.",
             "Pipeline time includes READY, work and feedback preflight; independent final grading excluded "
             "for both. Token counts include READY and work; local grading uses no model tokens. Provider "
             "USD is an estimate, not a bill. All failures remain in the denominator.", "",
             "| Arm | Defect repaired | Clean unchanged | Clean regressions | Full PASS | Median seconds | Tokens | Reported USD | pass^" + str(repeats) + " cases |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        group = [x for x in rows if x["arm"] == arm]
        defects = [x for x in group if x["kind"] == "defect"]
        controls = [x for x in group if x["kind"] == "clean"]
        good = sum(x["pass_trial"] for x in group)
        both = sum(all(x["pass_trial"] for x in group if x["case"] == case) for case in cases)
        lines.append(f"| {arm} | {sum(x['pass_trial'] for x in defects)}/{len(defects)} | "
                     f"{sum(not x['changed'] for x in controls)}/{len(controls)} | "
                     f"{sum(not (x['frozen']['passed'] and x['golden']['passed']) for x in controls)} | "
                     f"{good}/{len(group)} | "
                     f"{statistics.median(x['pipeline_seconds'] for x in group):.2f} | "
                     f"{sum(x['usage']['total'] for x in group)} | "
                     f"{sum(x['usage']['cost_usd'] for x in group):.6f} | {both}/{len(cases)} |")
    lines += ["", "## Limits", "", "These tiny synthetic cases are exploratory. Clean unchanged is only an "
              "over-edit proxy, not a production TNR; a clean candidate can still have untested defects. "
              "No representative incident sampling or blinded reviewer quality is measured. Model stochasticity "
              "and provider caching are uncontrolled. Original Brokan acceptance remains unchanged.", ""]
    (root / "summary.md").write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "matrix", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--cohort", choices=tuple(COHORTS), default="pilot")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "preflight":
        if root.exists():
            parser.error("preflight root must be new")
        root.mkdir(mode=0o700)
        for case in COHORTS[args.cohort]:
            good = check(seed(case), frozen(case), root / f"{case}-frozen")
            held = check(seed(case), golden(case), root / f"{case}-golden")
            assert good["passed"] and held["passed"] == clean(case) and held["tests"] >= 2, f"invalid seed: {case}"
            print(f"{case}: frozen {good['tests']} PASS; golden {held['tests']} "
                  + ("GREEN" if clean(case) else "RED"))
    elif args.action == "matrix":
        if args.repeats < 2 or args.repeats > 3 or root.exists():
            parser.error("matrix root must be new, repeats in [2,3]")
        root.mkdir(mode=0o700)
        cases = COHORTS[args.cohort]
        save(root / "manifest.json", {"runner_sha256": sha(Path(__file__).read_bytes()),
              "fixture_commit": FIXTURE_COMMIT, "model": MODEL, "thinking": THINKING,
              "cohort": args.cohort, "cases": list(cases),
              "sources": {case: source_hashes(case) for case in cases},
              "repeats": args.repeats,
              "pi_version": subprocess.run(["pi", "--version"], capture_output=True,
                                           text=True, check=True).stdout.strip()})
        for r in range(1, args.repeats + 1):
            for case in cases:
                for arm in (ARMS if r % 2 else tuple(reversed(ARMS))):
                    result = trial(root, case, arm, r, contract(case).decode())
                    if not result["complete_usage"]:
                        raise RuntimeError("provider stage incomplete; retain private partial matrix, do not retry in place")
        rows = verify(root, args.repeats)
        summarize(root, rows, args.repeats, args.cohort)
    else:
        manifest = json.loads((root / "manifest.json").read_text())
        rows = verify(root, manifest["repeats"])
        summarize(root, rows, manifest["repeats"], manifest["cohort"])
        print(f"PASS: {len(rows)} matched trials, verified private receipts")


if __name__ == "__main__":
    main()
