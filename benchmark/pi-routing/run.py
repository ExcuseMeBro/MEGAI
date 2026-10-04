#!/usr/bin/env python3
"""Paired native Pi worker + GPT review benchmark; private evidence, no host edits."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time

BASELINE = "095a664e7fb8519a69e0bff9f0b1d452c26e4cf1"
GPT = "openai-codex/gpt-6.1-sol"
DEEPSEEK = "deepseek/deepseek-flash"
FALLBACK = "openai-codex/gpt-5.6-luna"
MODULES = {"bugfix": "intervals.py", "feature": "batching.py", "refactor": "reporting.py"}
ARMS = ("gpt-only", "deepseek-gpt")
REPO = Path(__file__).resolve().parents[2]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n")


def parse_events(text: str) -> dict:
    usage = dict(input=0, output=0, cache_read=0, cache_write=0, reasoning=0, total=0, cost_usd=0.0)
    models, stops, errors, final = set(), [], [], ""
    requests = 0
    complete_usage = True
    for line in text.split("\n"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "message_end":
            message = event.get("message", {})
            if message.get("role") != "assistant":
                continue
            requests += 1
            models.add(f"{message.get('provider')}/{message.get('model')}")
            stops.append(message.get("stopReason"))
            if message.get("stopReason") in ("error", "aborted"):
                errors.append(message.get("errorMessage") or message.get("stopReason"))
            final = "\n".join(b.get("text", "") for b in message.get("content", []) if b.get("type") == "text")
            counters = message.get("usage")
        elif event.get("type") == "compaction_end" and event.get("result"):
            counters = event["result"].get("usage")
        elif event.get("type") == "entry_appended" and event.get("entry", {}).get("type") == "usage":
            counters = event["entry"].get("usage")
        else:
            continue
        if not isinstance(counters, dict) or "totalTokens" not in counters:
            complete_usage = False
            continue
        for dest, key in [("input", "input"), ("output", "output"), ("cache_read", "cacheRead"),
                          ("cache_write", "cacheWrite"), ("reasoning", "reasoning"), ("total", "totalTokens")]:
            usage[dest] += counters.get(key) or 0
        usage["cost_usd"] += (counters.get("cost") or {}).get("total") or 0.0
    return dict(usage=usage, requests=requests, models=sorted(models), stops=stops,
                errors=errors, final=final, complete_usage=complete_usage and requests > 0)


def aggregate(stages: list[dict]) -> dict:
    result = {key: sum(s["usage"][key] for s in stages) for key in stages[0]["usage"]}
    result["cost_usd"] = round(result["cost_usd"], 8)
    return result


def balance_error(stage: dict) -> bool:
    return stage["model"] == DEEPSEEK and any(
        "402" in error and "insufficient balance" in error.lower() for error in stage["errors"]
    )


def native_identity(directory: Path, model: str, thinking: str) -> bool:
    files = list(directory.glob("*.jsonl"))
    if len(files) != 1:
        return False
    selected, level = None, None
    for line in files[0].read_text().split("\n"):
        if not line:
            continue
        entry = json.loads(line)
        if entry.get("type") == "model_change":
            selected = f"{entry.get('provider')}/{entry.get('modelId')}"
        elif entry.get("type") == "thinking_level_change":
            level = entry.get("thinkingLevel")
    return selected == model and level == thinking


def invoke(cwd: Path, directory: Path, model: str, thinking: str, prompt: str,
           tools: bool, session_dir: Path, resume: bool = False) -> dict:
    directory.mkdir()
    (directory / "prompt.txt").write_text(prompt)
    cmd = ["pi", "-p", "--mode", "json", "--no-extensions", "--no-skills", "--no-context-files",
           "--no-prompt-templates", "--no-themes", "--no-approve", "--offline",
           "--model", model, "--thinking", thinking, "--session-dir", str(session_dir)]
    cmd += ["--tools", "read,bash,edit,write"] if tools else ["--no-tools"]
    if resume:
        cmd += ["--session", str(next(session_dir.glob("*.jsonl")))]
    cmd += [prompt]
    start = time.monotonic()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for key in ("PI_SESSION_ID", "PI_SESSION_FILE", "PI_PROVIDER", "PI_MODEL", "PI_REASONING_LEVEL"):
        env.pop(key, None)
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    duration = time.monotonic() - start
    (directory / "events.jsonl").write_text(proc.stdout)
    (directory / "stderr.txt").write_text(proc.stderr)
    parsed = parse_events(proc.stdout)
    parsed.update(model=model, thinking=thinking, seconds=duration, exit=proc.returncode,
                  command=cmd, identity_ok=native_identity(session_dir, model, thinking))
    save(directory / "receipt.json", parsed)
    return parsed


def stage_ok(stage: dict) -> bool:
    return (stage["exit"] == 0 and stage["identity_ok"] and stage["models"] == [stage["model"]]
            and bool(stage["stops"]) and stage["stops"][-1] == "stop" and not stage["errors"])


def role(cwd: Path, directory: Path, model: str, thinking: str, prompt: str, tools: bool) -> list[dict]:
    directory.mkdir()
    sessions = directory / "sessions"
    sessions.mkdir()
    ready = invoke(cwd, directory / "ready", model, thinking,
                   "Reply exactly READY. Do not use tools or inspect files.", False, sessions)
    stages = [ready]
    if stage_ok(ready) and ready["final"].strip() == "READY":
        stages.append(invoke(cwd, directory / "task", model, thinking, prompt, tools, sessions, True))
    return stages


def baseline_file(path: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{BASELINE}:{path}"],
                          check=True, capture_output=True).stdout


def inventory(root: Path) -> dict:
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            result[str(path.relative_to(root))] = "symlink"
        elif path.is_file():
            result[str(path.relative_to(root))] = digest(path.read_bytes())
    return result


def evaluate(candidate: Path, directory: Path, task: str, original_test: bytes) -> dict:
    directory.mkdir()
    module = MODULES[task]
    (directory / module).write_bytes((candidate / module).read_bytes())
    (directory / "test_acceptance.py").write_bytes(original_test)
    cmd = [sys.executable, "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test_acceptance.py", "-v"]
    start = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(cmd, cwd=directory, capture_output=True, text=True, check=False, timeout=30)
        output, exit_code = proc.stdout + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as error:
        timed_out = True
        def decoded(value):
            return value.decode(errors="replace") if isinstance(value, bytes) else (value or "")
        output = decoded(error.stdout) + decoded(error.stderr) + "\nEVALUATOR TIMEOUT (30s)\n"
        exit_code = None
    (directory / "output.txt").write_text(output)
    count = re.search(r"Ran (\d+) tests?", output)
    result = dict(exit=exit_code, timed_out=timed_out, tests=int(count.group(1)) if count else 0,
                  passed=exit_code == 0 and count is not None, seconds=time.monotonic() - start,
                  test_sha256=digest(original_test), module_sha256=digest((candidate / module).read_bytes()))
    save(directory / "receipt.json", result)
    return result


def run_trial(root: Path, task: str, arm: str, repeat: int, spec: str) -> dict:
    directory = root / f"r{repeat}-{task}-{arm}"
    directory.mkdir()
    cwd = directory / "candidate"
    cwd.mkdir()
    module = MODULES[task]
    prefix = f"capy/benchmark/cases/{task}/"
    initial = baseline_file(prefix + module)
    tests = baseline_file(prefix + "test_acceptance.py")
    (cwd / module).write_bytes(initial)
    (cwd / "test_acceptance.py").write_bytes(tests)
    before = inventory(cwd)
    started = time.monotonic()
    model, thinking = (GPT, "medium") if arm == "gpt-only" else (DEEPSEEK, "high")
    prompt = (
        "You are a benchmark leaf. Parent owns Plane MEGAI-188. Do not delegate, mutate Plane, "
        "commit, install packages, use network, read other trials or access files outside cwd. "
        f"Only write {module} and test_participant.py. test_acceptance.py is immutable. "
        f"Complete the {task} contract below. Plan briefly, implement and add meaningful tests. "
        "For refactor first run existing characterization tests and remove duplicated counting/validation. "
        "Run python3 -B -m unittest discover -s . -p 'test_*.py' -v. "
        "Self-review and return changed files plus actual tests in at most six bullets.\n\n" + spec
    )
    stages = role(cwd, directory / "worker", model, thinking, prompt, True)
    fallback = balance_error(stages[-1])
    if fallback:
        stages += role(cwd, directory / "fallback", FALLBACK, "medium", prompt, True)
    evaluation = evaluate(cwd, directory / "evaluation", task, tests)
    after = inventory(cwd)
    changes = sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))
    scope_ok = set(changes) <= {module, "test_participant.py"} and after.get(module) != before[module]
    review_prompt = (
        "You are a read-only independent benchmark reviewer. Do not use tools or delegate. "
        "Review supplied contract, original and candidate implementation and evaluator output. "
        "For refactor check duplicated counting/validation is actually removed. "
        "Reply first line exactly PASS or FAIL, followed by concrete findings (max six bullets). "
        "A passing test alone does not establish maintainability or complete correctness.\n\n"
        + spec + "\n\nORIGINAL:\n" + initial.decode() + "\n\nCANDIDATE:\n"
        + (cwd / module).read_text() + "\n\nPARTICIPANT TESTS:\n"
        + ((cwd / "test_participant.py").read_text() if (cwd / "test_participant.py").exists() else "MISSING")
        + "\n\nEVALUATOR:\n" + (directory / "evaluation/output.txt").read_text()
    )
    reviewer = role(cwd, directory / "reviewer", GPT, "medium", review_prompt, False)
    stages += reviewer
    review_ok = stage_ok(reviewer[-1]) and reviewer[-1]["final"].split("\n")[0].strip() == "PASS"
    model_ok = all(stage_ok(s) for s in stages if not balance_error(s))
    result = dict(arm=arm, task=task, repeat=repeat, baseline=BASELINE,
                  seconds=time.monotonic() - started, usage=aggregate(stages),
                  complete_usage=all(s["complete_usage"] for s in stages),
                  acceptance=evaluation, review_pass=review_ok, scope_ok=scope_ok,
                  fallback=fallback, actual_models=sorted({m for s in stages for m in s["models"]}),
                  pass_trial=evaluation["passed"] and review_ok and scope_ok and model_ok,
                  stage_paths=[str(p.relative_to(root)) for p in directory.glob("*/**/receipt.json")
                               if "sessions" not in p.parts and "evaluation" not in p.parts],
                  changed_files=changes)
    save(directory / "result.json", result)
    print(json.dumps({k: result[k] for k in ("arm", "task", "repeat", "seconds", "usage", "pass_trial", "fallback")}), flush=True)
    return result


def repair(root: Path) -> None:
    for original in sorted(root.glob("r*-deepseek-gpt/result.json")):
        row = json.loads(original.read_text())
        if row["pass_trial"] or row["review_pass"]:
            continue
        trial = original.parent
        directory = trial / "repair"
        directory.mkdir()
        cwd = directory / "candidate"
        cwd.mkdir()
        for path in (trial / "candidate").iterdir():
            if path.is_file():
                (cwd / path.name).write_bytes(path.read_bytes())
        module = MODULES[row["task"]]
        started = time.monotonic()
        feedback = json.loads((trial / "reviewer/task/receipt.json").read_text())["final"]
        spec = baseline_file("capy/benchmark/tasks.md").decode()
        prompt = (
            "Benchmark leaf, Plane MEGAI-188. Do not delegate, mutate Plane, install, commit, "
            "use network or access paths outside cwd. Only write " + module + " and test_participant.py. "
            "Repair this reviewer-confirmed failure, add a regression for it, and run all tests. "
            "test_acceptance.py is immutable. Return actual test results.\n\n" + feedback + "\n\n" + spec
        )
        stages = role(cwd, directory / "worker", DEEPSEEK, "high", prompt, True)
        tests = baseline_file(f"capy/benchmark/cases/{row['task']}/test_acceptance.py")
        evaluation = evaluate(cwd, directory / "evaluation", row["task"], tests)
        # This follow-up was prompted by a concrete review finding; its extra probe
        # does not retroactively replace the frozen initial acceptance suite.
        probe = {
            "feature": "from batching import chunked; assert list(chunked([1], 10**100)) == [[1]]",
            "bugfix": "from intervals import merge_intervals; assert merge_intervals([(1,10),(2,3)]) == [(1,10)]",
            "refactor": "from reporting import render_checks; assert render_checks([]) == 'TOTAL 0 | PASS 0 | FAIL 0 | SKIP 0'",
        }[row["task"]]
        proc = subprocess.run([sys.executable, "-B", "-c", probe], cwd=cwd,
                              capture_output=True, text=True, check=False, timeout=30)
        (directory / "regression.txt").write_text(proc.stdout + proc.stderr)
        review = role(cwd, directory / "reviewer", GPT, "medium",
            "Independent read-only reviewer; no tools. Reply first line PASS or FAIL. "
            "Review the repair against the contract and prior finding.\n" + spec + "\n" + feedback
            + "\nCANDIDATE:\n" + (cwd / module).read_text()
            + "\nPARTICIPANT TESTS:\n" + (cwd / "test_participant.py").read_text()
            + f"\nFrozen acceptance: {evaluation}. Task-specific regression exit: {proc.returncode}.", False)
        stages += review
        review_ok = stage_ok(review[-1]) and review[-1]["final"].split("\n")[0].strip() == "PASS"
        before, after = inventory(trial / "candidate"), inventory(cwd)
        scope_ok = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)} <= {module, "test_participant.py"}
        result = dict(original_trial=trial.name, seconds=time.monotonic() - started,
                      usage=aggregate(stages), original_seconds=row["seconds"], original_usage=row["usage"],
                      acceptance=evaluation, regression_exit=proc.returncode, review_pass=review_ok,
                      pass_repair=evaluation["passed"] and proc.returncode == 0 and review_ok and scope_ok
                                  and all(stage_ok(s) for s in stages),
                      stage_paths=[str(p.relative_to(root)) for p in directory.glob("*/**/receipt.json")
                                   if "sessions" not in p.parts and "evaluation" not in p.parts])
        result["end_to_end_seconds"] = row["seconds"] + result["seconds"]
        result["end_to_end_usage"] = aggregate([row, result])
        save(directory / "result.json", result)
        print(json.dumps(result), flush=True)
    manifest = json.loads((root / "manifest.json").read_text())
    summarize(root, manifest["repeats"])


def summarize(root: Path, repeats: int) -> list[dict]:
    rows = [json.loads(p.read_text()) for p in sorted(root.glob("r*-*/result.json"))]
    save(root / "results.json", rows)
    lines = ["# Fresh Pi GPT-only vs DeepSeek + GPT", "",
             f"Frozen fixture commit: `{BASELINE}`. Repetitions per task/arm: {repeats}.", "",
             "Both arms use native Pi, a fresh worker and independent GPT Sol medium review. "
             "GPT-only worker: GPT Sol medium. Hybrid worker: DeepSeek Flash high. "
             "Only confirmed DeepSeek 402 balance errors use Luna medium; reported separately. "
             "READY identity checks, worker, fallback, review and evaluator time are included. "
             "Global skills/extensions/context discovery is disabled equally in both arms. "
             "This measures bounded fixture execution, not full production task/Plane/worktree overhead. "
             "Reported tokens include cache; reasoning is a separate counter, not added twice. "
             "Cost is catalog-reported, not a billing receipt. Provider caching is not forced cold. "
             "No automatic repair/retry loop is used; failures are retained.", "",
             "| Arm | Complete trials | Acceptance | Reviewed delivery | Fallbacks | Median seconds | Total tokens | Uncached input | Output | Cache read | Reported USD |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        group = [r for r in rows if r["arm"] == arm]
        if not group:
            continue
        usage = aggregate(group)
        lines.append(f"| {arm} | {len(group)}/{3 * repeats} | {sum(r['acceptance']['passed'] for r in group)}/{len(group)} | "
                     f"{sum(r['pass_trial'] for r in group)}/{len(group)} | {sum(r['fallback'] for r in group)} | "
                     f"{statistics.median(r['seconds'] for r in group):.2f} | {usage['total']} | "
                     f"{usage['input']} | {usage['output']} | {usage['cache_read']} | {usage['cost_usd']:.6f} |")
    lines += ["", "## Per task (median across repeats)", "",
              "| Task | Arm | Seconds | Tokens | Acceptance | Reviewed delivery |", "|---|---|---:|---:|---:|---:|"]
    for task in MODULES:
        for arm in ARMS:
            group = [r for r in rows if r["arm"] == arm and r["task"] == task]
            if group:
                lines.append(f"| {task} | {arm} | {statistics.median(r['seconds'] for r in group):.2f} | "
                             f"{statistics.median(r['usage']['total'] for r in group):.0f} | "
                             f"{sum(r['acceptance']['passed'] for r in group)}/{len(group)} | {sum(r['pass_trial'] for r in group)}/{len(group)} |")
    repairs = [json.loads(p.read_text()) for p in sorted(root.glob("r*-*/repair/result.json"))]
    if repairs:
        repaired = {r["original_trial"]: r for r in repairs}
        hybrid = [r for r in rows if r["arm"] == "deepseek-gpt"]
        adjusted = [{**r, "usage": repaired[f"r{r['repeat']}-{r['task']}-{r['arm']}"]["end_to_end_usage"],
                     "seconds": repaired[f"r{r['repeat']}-{r['task']}-{r['arm']}"]["end_to_end_seconds"],
                     "pass_trial": repaired[f"r{r['repeat']}-{r['task']}-{r['arm']}"]["pass_repair"]}
                    if f"r{r['repeat']}-{r['task']}-{r['arm']}" in repaired else r for r in hybrid]
        usage = aggregate(adjusted)
        lines += ["", "## Separate bounded repair follow-up", "",
                  "Original failures above remain unchanged. Only review-confirmed failures receive one "
                  "DeepSeek repair plus a fresh GPT review; all added stage cost/time is included below. "
                  "No failed initial candidate is overwritten.", "",
                  f"Repairs: {sum(r['pass_repair'] for r in repairs)}/{len(repairs)}. "
                  f"Hybrid reviewed delivery after repair: {sum(r['pass_trial'] for r in adjusted)}/{len(adjusted)}. "
                  f"Median end-to-end: {statistics.median(r['seconds'] for r in adjusted):.2f}s. "
                  f"Total tokens: {usage['total']}; uncached input: {usage['input']}; "
                  f"output: {usage['output']}; cache read: {usage['cache_read']}; "
                  f"reported USD: {usage['cost_usd']:.6f}."]
        save(root / "repair-results.json", repairs)
    (root / "summary.md").write_text("\n".join(lines) + "\n")
    return rows


def verify(root: Path) -> None:
    manifest = json.loads((root / "manifest.json").read_text())
    rows = summarize(root, manifest["repeats"])
    expected = {(a, t, r) for a in ARMS for t in MODULES for r in range(1, manifest["repeats"] + 1)}
    assert {(r["arm"], r["task"], r["repeat"]) for r in rows} == expected, "incomplete paired matrix"
    assert len(rows) == len(expected), "duplicate trials"
    for row in rows:
        assert row["complete_usage"], "missing provider usage"
        trial = root / f"r{row['repeat']}-{row['task']}-{row['arm']}"
        stages = []
        for relative in row["stage_paths"]:
            receipt = root / relative
            stage = json.loads(receipt.read_text())
            parsed = parse_events((receipt.parent / "events.jsonl").read_text())
            assert stage["usage"] == parsed["usage"], "usage drift"
            for key in ("models", "stops", "errors", "final", "requests", "complete_usage"):
                assert stage[key] == parsed[key], f"{key} evidence drift"
            assert native_identity(receipt.parent.parent / "sessions", stage["model"], stage["thinking"]), "identity drift"
            stages.append(stage)
        assert len(stages) >= 4, "missing worker/reviewer receipts"
        assert aggregate(stages) == row["usage"], "total excludes stage usage"
        assert row["seconds"] >= sum(s["seconds"] for s in stages), "wall time excludes stages"
        evaluation = json.loads((trial / "evaluation/receipt.json").read_text())
        assert evaluation == row["acceptance"], "acceptance receipt drift"
        assert evaluation["test_sha256"] == digest(baseline_file(f"capy/benchmark/cases/{row['task']}/test_acceptance.py")), "tests modified"
        assert evaluation["module_sha256"] == digest((trial / "candidate" / MODULES[row["task"]]).read_bytes()), "candidate drift"
        reviewer = json.loads((trial / "reviewer/task/receipt.json").read_text())
        review_ok = stage_ok(reviewer) and reviewer["final"].split("\n")[0].strip() == "PASS"
        assert row["review_pass"] == review_ok, "review verdict evidence drift"
        model_ok = all(stage_ok(s) for s in stages if not balance_error(s))
        assert row["pass_trial"] == (evaluation["passed"] and review_ok and row["scope_ok"] and model_ok), "delivery verdict evidence drift"
    for path in root.glob("r*-*/repair/result.json"):
        repair_row = json.loads(path.read_text())
        stages = []
        for relative in repair_row["stage_paths"]:
            receipt = root / relative
            stage = json.loads(receipt.read_text())
            parsed = parse_events((receipt.parent / "events.jsonl").read_text())
            for key in ("usage", "models", "stops", "errors", "final", "requests", "complete_usage"):
                assert stage[key] == parsed[key], f"repair {key} evidence drift"
            assert native_identity(receipt.parent.parent / "sessions", stage["model"], stage["thinking"])
            stages.append(stage)
        assert aggregate(stages) == repair_row["usage"]
        original = json.loads((path.parent.parent / "result.json").read_text())
        assert repair_row["end_to_end_usage"] == aggregate([original, repair_row])
        assert repair_row["end_to_end_seconds"] == original["seconds"] + repair_row["seconds"]
        assert repair_row["seconds"] >= sum(s["seconds"] for s in stages)
        evaluation = json.loads((path.parent / "evaluation/receipt.json").read_text())
        assert evaluation == repair_row["acceptance"]
        assert evaluation["module_sha256"] == digest((path.parent / "candidate" / MODULES[original["task"]]).read_bytes())
        assert evaluation["test_sha256"] == original["acceptance"]["test_sha256"]
        reviewer = json.loads((path.parent / "reviewer/task/receipt.json").read_text())
        review_ok = stage_ok(reviewer) and reviewer["final"].split("\n")[0].strip() == "PASS"
        assert repair_row["review_pass"] == review_ok, "repair review verdict evidence drift"
        assert not repair_row["pass_repair"] or (evaluation["passed"] and review_ok and repair_row["regression_exit"] == 0 and all(stage_ok(s) for s in stages)), "repair delivery verdict evidence drift"
    print(f"PASS: complete {len(rows)}-trial matrix; failures retained, stage accounting and immutable evaluator receipts verified")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("matrix", "repair", "summarize", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "matrix":
        if args.repeats < 1:
            parser.error("repeats must be positive")
        root.mkdir(parents=True, mode=0o700)
        os.chmod(root, 0o700)
        spec = baseline_file("capy/benchmark/tasks.md").decode()
        save(root / "manifest.json", dict(repeats=args.repeats, baseline=BASELINE,
             gpt=GPT, deepseek=DEEPSEEK, fallback=FALLBACK, fallback_thinking="medium",
             pi_version=subprocess.run(["pi", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
             runner_sha256=digest(Path(__file__).read_bytes())))
        for repeat in range(1, args.repeats + 1):
            for task in MODULES:
                order = ARMS if repeat % 2 else tuple(reversed(ARMS))
                for arm in order:
                    run_trial(root, task, arm, repeat, spec)
                    summarize(root, args.repeats)
        verify(root)
    elif args.action == "repair":
        repair(root)
        verify(root)
    elif args.action == "verify":
        verify(root)
    else:
        summarize(root, json.loads((root / "manifest.json").read_text())["repeats"])


if __name__ == "__main__":
    main()
