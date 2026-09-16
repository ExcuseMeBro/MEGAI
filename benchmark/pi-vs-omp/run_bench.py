#!/usr/bin/env python3
"""Pi vs OMP harness benchmark on frozen MEGAI fixtures.

Subcommands:
  overhead   measure per-arm baseline context tokens with a trivial prompt
  trial      run one arm/model/thinking/task trial and record its evidence
  matrix     run the trial matrix sequentially (resumable)
  summarize  build comparison tables from results.jsonl

Raw evidence (candidate diffs, harness streams, evaluation output) stays in the
private --root directory. Only the sanitized record and the summary are published.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

PLANE_PROJECT = "59005e36-ecd4-46ed-bb42-f779858b20ce"
PLANE_TASK = "8da0cfa6-7759-4fee-8964-88c7d967897e"

ARMS = ("pi", "omp")
MODELS = (
    "deepseek/deepseek-flash",
    "openai-codex/gpt-6-astra",
    "openai-codex/gpt-5.6-sol",
    "openai-codex/gpt-5.6-luna",
)
THINKING_LEVELS = ("high", "medium")
TASK_IMPL = {
    "bugfix": "capy/benchmark/cases/bugfix/intervals.py",
    "feature": "capy/benchmark/cases/feature/batching.py",
    "refactor": "capy/benchmark/cases/refactor/reporting.py",
}
PARTICIPANT = "test_participant.py"
BUDGET_SECONDS = 300
SHORT_MODEL = {
    "deepseek/deepseek-flash": "deepseek-flash",
    "openai-codex/gpt-6-astra": "gpt-6-astra",
    "openai-codex/gpt-5.6-sol": "gpt-5.6-sol",
    "openai-codex/gpt-5.6-luna": "gpt-5.6-luna",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd, cwd=None, timeout=None, env=None):
    return subprocess.run(
        cmd, cwd=cwd, env=env, timeout=timeout, capture_output=True, text=True, check=False
    )


def harness_command(arm: str, model: str, thinking: str, prompt: str) -> list[str]:
    if arm == "pi":
        return [
            "pi", "-p", "--mode", "json", "--no-session", "-a",
            "--model", model, "--thinking", thinking, prompt,
        ]
    return [
        "omp", "-p", "--mode", "json", "--no-session", "--auto-approve",
        "--model", model, f"--thinking={thinking}", prompt,
    ]


def harness_version(arm: str) -> str:
    result = run([arm, "--version"])
    text = (result.stdout or result.stderr or "").strip().splitlines()
    return text[0].strip() if text else "unknown"


def clone_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    clone = subprocess.run(["cp", "-Rc", str(src), str(dst)], capture_output=True, text=True)
    if clone.returncode != 0:
        shutil.copytree(src, dst, symlinks=True)


def git(repo: Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args]).stdout


def allowed_paths(task: str) -> set[str]:
    impl = TASK_IMPL[task]
    return {impl, f"{Path(impl).parent}/{PARTICIPANT}"}


def render_prompt(task: str, model: str, thinking: str, arm: str) -> str:
    text = (HERE / "prompts" / f"{task}.md").read_text()
    values = {
        "MODEL": model,
        "THINKING": thinking,
        "ARM": arm,
        "CASE": str(Path(TASK_IMPL[task]).parent),
        "TASK": TASK_IMPL[task],
        "PLANE_PROJECT": PLANE_PROJECT,
        "PLANE_TASK": PLANE_TASK,
    }
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftovers = re.findall(r"\{\{[A-Z_]+\}\}", text)
    if leftovers:
        raise SystemExit(f"unfilled prompt placeholders: {leftovers}")
    return text


def parse_events(path: Path) -> dict:
    usage = {"input": 0, "output": 0, "cache_read": 0, "reasoning": 0, "total": 0, "cost_usd": 0.0}
    requests = 0
    models: set[str] = set()
    stops: list[str] = []
    if path.exists():
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "turn_end":
                continue
            message = event.get("message") or {}
            if message.get("role") != "assistant":
                continue
            counters = message.get("usage") or {}
            requests += 1
            usage["input"] += counters.get("input") or 0
            usage["output"] += counters.get("output") or 0
            usage["cache_read"] += counters.get("cacheRead") or 0
            usage["reasoning"] += (counters.get("reasoning") or 0) + (
                counters.get("reasoningTokens") or 0
            )
            usage["total"] += counters.get("totalTokens") or 0
            usage["cost_usd"] += (counters.get("cost") or {}).get("total") or 0.0
            if message.get("model"):
                models.add(f"{message.get('provider', '')}/{message.get('model')}")
            if message.get("stopReason"):
                stops.append(str(message["stopReason"]))
    usage["cost_usd"] = round(usage["cost_usd"], 6)
    return {"requests": requests, "usage": usage, "reported_models": sorted(models), "stop_reasons": stops}


def run_suite(root: Path, case: str, pattern: str) -> dict:
    target = root / case / pattern
    if pattern == PARTICIPANT and not target.exists():
        return {"present": False, "ok": None, "tests": None, "exit_status": None}
    proc = run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", case, "-p", pattern, "-v"],
        cwd=root,
        timeout=900,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    ran = re.search(r"Ran (\d+) tests?", output)
    failed = re.search(r"FAILED \(([^)]*)\)", output)
    return {
        "present": True,
        "ok": proc.returncode == 0,
        "tests": int(ran.group(1)) if ran else None,
        "failures": failed.group(1) if failed else None,
        "exit_status": proc.returncode,
        "output_tail": "\n".join(output.strip().splitlines()[-8:]),
    }


def evaluate(baseline: Path, repo: Path, task: str, eval_dir: Path) -> tuple[dict, dict]:
    clone_tree(baseline, eval_dir)
    for rel in sorted(allowed_paths(task)):
        src = repo / rel
        dst = eval_dir / rel
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        elif dst.exists():
            dst.unlink()
    case = str(Path(TASK_IMPL[task]).parent)
    return run_suite(eval_dir, case, "test_acceptance.py"), run_suite(eval_dir, case, PARTICIPANT)


def trial_id(arm: str, model: str, thinking: str, task: str) -> str:
    return "__".join([arm, slug(SHORT_MODEL.get(model, model)), thinking, task])


def run_trial(arm, model, thinking, task, baseline, root, budget, versions) -> dict:
    identity = trial_id(arm, model, thinking, task)
    trial_dir = root / "trials" / identity
    if trial_dir.exists():
        shutil.rmtree(trial_dir)
    trial_dir.mkdir(parents=True)
    repo = trial_dir / "repo"
    clone_tree(baseline, repo)

    prompt = render_prompt(task, model, thinking, arm)
    prompt_path = trial_dir / "prompt.md"
    prompt_path.write_text(prompt)
    stdout_path = trial_dir / "harness.jsonl"
    stderr_path = trial_dir / "harness.stderr.txt"

    env = os.environ.copy()
    env.pop("PI_CONFIG_FILES", None)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    started = time.time()
    timed_out = False
    with stdout_path.open("w") as out, stderr_path.open("w") as err:
        try:
            proc = subprocess.run(
                harness_command(arm, model, thinking, prompt),
                cwd=repo, env=env, stdout=out, stderr=err, timeout=budget,
            )
            exit_status = proc.returncode
        except subprocess.TimeoutExpired:
            exit_status = None
            timed_out = True
    wall_seconds = round(time.time() - started, 3)

    git(repo, "add", "-A", "-N")
    changed = [line for line in git(repo, "diff", "--name-only").splitlines() if line.strip()]
    diff_text = git(repo, "diff")
    (trial_dir / "candidate.diff").write_text(diff_text)
    events = parse_events(stdout_path)
    acceptance, participant = evaluate(baseline, repo, task, trial_dir / "eval")

    record = {
        "trial_id": identity,
        "arm": arm,
        "model": model,
        "model_short": SHORT_MODEL.get(model, model),
        "thinking": thinking,
        "task": task,
        "baseline_sha": git(baseline, "rev-parse", "HEAD").strip(),
        "prompt_sha256": sha256_file(prompt_path),
        "prompt_chars": len(prompt),
        "harness_version": versions.get(arm, "unknown"),
        "started_at": started_at,
        "wall_seconds": wall_seconds,
        "budget_seconds": budget,
        "exit_status": exit_status,
        "timed_out": timed_out,
        "requests": events["requests"],
        "usage": events["usage"],
        "reported_models": events["reported_models"],
        "model_matches_request": events["reported_models"] == [arm_model_id(arm, model)]
        if events["reported_models"]
        else None,
        "stop_reasons": events["stop_reasons"][-3:],
        "provider_error": any(reason == "error" for reason in events["stop_reasons"]),
        "changed_paths": changed,
        "scope_ok": set(changed) <= allowed_paths(task),
        "diff_bytes": len(diff_text),
        "diff_sha256": hashlib.sha256(diff_text.encode()).hexdigest(),
        "acceptance": acceptance,
        "participant": participant,
        "stderr_bytes": stderr_path.stat().st_size,
    }
    record["valid"] = (
        record["requests"] > 0
        and record["usage"]["total"] > 0
        and not record["provider_error"]
        and not record["timed_out"]
        and wall_seconds <= budget
    )
    (trial_dir / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def arm_model_id(arm: str, model: str) -> str:
    provider, _, name = model.partition("/")
    return f"{provider}/{name}"


def append_result(results_path: Path, record: dict) -> None:
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a") as handle:
        handle.write(json.dumps(record) + "\n")


def load_results(results_path: Path) -> list[dict]:
    if not results_path.exists():
        return []
    rows = []
    for line in results_path.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def arm_order(task: str) -> tuple[str, ...]:
    return ("pi", "omp") if task in ("bugfix", "refactor") else ("omp", "pi")


def cmd_trial(args) -> int:
    versions = {arm: harness_version(arm) for arm in ARMS}
    record = run_trial(
        args.arm, args.model, args.thinking, args.task,
        Path(args.baseline).resolve(), Path(args.root).resolve(),
        args.budget, versions,
    )
    append_result(Path(args.results).resolve(), record)
    print(json.dumps({
        "trial_id": record["trial_id"],
        "wall_seconds": record["wall_seconds"],
        "requests": record["requests"],
        "usage": record["usage"],
        "scope_ok": record["scope_ok"],
        "timed_out": record["timed_out"],
        "acceptance": record["acceptance"].get("ok"),
        "acceptance_tests": record["acceptance"].get("tests"),
    }))
    return 0


def cmd_matrix(args) -> int:
    baseline = Path(args.baseline).resolve()
    root = Path(args.root).resolve()
    results_path = Path(args.results).resolve()
    arms = tuple(args.arms.split(",")) if args.arms else ARMS
    models = tuple(args.models.split(",")) if args.models else MODELS
    thinkings = tuple(args.thinkings.split(",")) if args.thinkings else THINKING_LEVELS
    tasks = tuple(args.tasks.split(",")) if args.tasks else tuple(TASK_IMPL)
    versions = {arm: harness_version(arm) for arm in arms}
    done = {row["trial_id"] for row in load_results(results_path)}
    print(f"versions: {versions} | already recorded: {len(done)}", flush=True)
    for model in models:
        for thinking in thinkings:
            for task in tasks:
                for arm in arm_order(task):
                    if arm not in arms:
                        continue
                    identity = trial_id(arm, model, thinking, task)
                    if identity in done:
                        print(f"skip {identity}", flush=True)
                        continue
                    record = run_trial(arm, model, thinking, task, baseline, root, args.budget, versions)
                    append_result(results_path, record)
                    acceptance = record["acceptance"]
                    print(
                        f"{record['trial_id']}: wall={record['wall_seconds']}s "
                        f"req={record['requests']} in={record['usage']['input']} "
                        f"out={record['usage']['output']} cache={record['usage']['cache_read']} "
                        f"total={record['usage']['total']} cost=${record['usage']['cost_usd']} "
                        f"accept={acceptance.get('tests')} ok={acceptance.get('ok')} "
                        f"scope_ok={record['scope_ok']} timeout={record['timed_out']} "
                        f"models={record['reported_models']}",
                        flush=True,
                    )
    return 0


def cmd_overhead(args) -> int:
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    cwd = Path(args.cwd).resolve()
    records = []
    for arm in (args.arms.split(",") if args.arms else ARMS):
        for rep in range(1, args.reps + 1):
            stdout_path = root / f"overhead-{arm}-{rep}.jsonl"
            env = os.environ.copy()
            env.pop("PI_CONFIG_FILES", None)
            started = time.time()
            with stdout_path.open("w") as out, (root / "overhead.err.txt").open("a") as err:
                run_command = harness_command(arm, args.model, "off", "Reply with exactly: OK")
                subprocess.run(run_command, cwd=cwd, env=env, stdout=out, stderr=err, check=False)
            events = parse_events(stdout_path)
            records.append({
                "arm": arm, "rep": rep, "wall_seconds": round(time.time() - started, 3),
                "model": args.model, "usage": events["usage"], "requests": events["requests"],
                "harness_version": harness_version(arm),
            })
            print(json.dumps(records[-1]), flush=True)
    (root / "overhead.json").write_text(json.dumps(records, indent=2) + "\n")
    return 0


def fmt_seconds(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def cmd_summarize(args) -> int:
    recorded = load_results(Path(args.results).resolve())
    if not recorded:
        raise SystemExit("no results recorded")
    rows = [row for row in recorded if row.get("valid", True)]
    excluded = [row for row in recorded if not row.get("valid", True)]
    overhead_path = Path(args.root).resolve() / "overhead.json"
    overhead = json.loads(overhead_path.read_text()) if overhead_path.exists() else []

    def accepted(row: dict) -> bool:
        return bool(row["acceptance"].get("ok"))

    lines: list[str] = []
    lines.append("# Pi vs OMP harness benchmark — results")
    lines.append("")
    lines.append(f"Baseline: `{rows[0]['baseline_sha']}` | valid trials: {len(rows)} | "
                 f"task budget: {rows[0]['budget_seconds']}s")
    lines.append("")
    if excluded:
        lines.append(f"Excluded as environment failures, not model results: {len(excluded)} "
                     "trial(s) with no provider usage, a provider error, or a run that "
                     "outlasted its budget.")
        lines.append("")
        lines.append("| Excluded trial | Wall s | Requests | Total tokens | Stop reasons |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in sorted(excluded, key=lambda r: r["trial_id"]):
            lines.append(
                f"| {row['trial_id']} | {fmt_seconds(row['wall_seconds'])} | {row['requests']} | "
                f"{row['usage']['total']} | {', '.join(row['stop_reasons']) or 'none'} |"
            )
        lines.append("")
    if overhead:
        lines.append("## Baseline harness context (trivial prompt, thinking off)")
        lines.append("")
        lines.append("Total tokens on a one-token reply = harness system prompt plus loaded "
                     "skills/rules for this checkout; uncached input shown from a cold cache run.")
        lines.append("")
        lines.append("| Arm | Harness | Reps | Median context tokens | Uncached input | Raw total |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for arm in sorted({row["arm"] for row in overhead}):
            subset = [row for row in overhead if row["arm"] == arm]
            totals = sorted(row["usage"]["total"] for row in subset)
            uncached = max(row["usage"]["input"] for row in subset)
            lines.append(
                f"| {arm} | {subset[0]['harness_version']} | {len(subset)} | "
                f"{totals[len(totals) // 2]} | {uncached} | {totals} |"
            )
        lines.append("")

    lines.append("## Per-trial results")
    lines.append("")
    lines.append("| Arm | Model | Thinking | Task | Wall s | Reqs | Input | Output | Cache read | "
                 "Total | Cost | Acceptance | Participant | Scope | Stop |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in sorted(rows, key=lambda r: (r["model_short"], r["thinking"], r["task"], r["arm"])):
        usage = row["usage"]
        acceptance = row["acceptance"]
        acc_text = f"{acceptance.get('tests')} {'PASS' if acceptance.get('ok') else 'FAIL'}"
        participant = row["participant"]
        part_text = "none" if not participant.get("present") else (
            f"{participant.get('tests')} {'PASS' if participant.get('ok') else 'FAIL'}"
        )
        stop = "deadline" if row["timed_out"] else f"exit {row['exit_status']}"
        lines.append(
            f"| {row['arm']} | {row['model_short']} | {row['thinking']} | {row['task']} | "
            f"{fmt_seconds(row['wall_seconds'])} | {row['requests']} | {usage['input']} | "
            f"{usage['output']} | {usage['cache_read']} | {usage['total']} | "
            f"${usage['cost_usd']:.4f} | {acc_text} | {part_text} | "
            f"{'ok' if row['scope_ok'] else 'violation'} | {stop} |"
        )
    lines.append("")

    lines.append("## Aggregate per arm × model × thinking")
    lines.append("")
    lines.append("| Arm | Model | Thinking | Tasks passed | Wall s (sum) | Wall s (median) | "
                 "Total tokens | Input | Output | Cost | Model mismatch |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    groups: dict[tuple[str, str, str], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["arm"], row["model_short"], row["thinking"]), []).append(row)
    for key in sorted(groups):
        subset = groups[key]
        walls = sorted(row["wall_seconds"] for row in subset)
        median = walls[len(walls) // 2]
        mismatch = any(row["model_matches_request"] is False for row in subset)
        lines.append(
            f"| {key[0]} | {key[1]} | {key[2]} | "
            f"{sum(1 for row in subset if accepted(row))}/{len(subset)} | "
            f"{sum(row['wall_seconds'] for row in subset):.1f} | {median:.1f} | "
            f"{sum(row['usage']['total'] for row in subset)} | "
            f"{sum(row['usage']['input'] for row in subset)} | "
            f"{sum(row['usage']['output'] for row in subset)} | "
            f"${sum(row['usage']['cost_usd'] for row in subset):.4f} | "
            f"{'YES' if mismatch else 'no'} |"
        )
    lines.append("")

    lines.append("## Harness headline (all models and levels together)")
    lines.append("")
    lines.append("| Arm | Trials | Acceptance | Wall s (sum) | Wall s (median) | Total tokens | "
                 "Input | Output | Cost | Scope violations | Deadlines |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for arm in sorted({row["arm"] for row in rows}):
        subset = [row for row in rows if row["arm"] == arm]
        walls = sorted(row["wall_seconds"] for row in subset)
        lines.append(
            f"| {arm} | {len(subset)} | {sum(1 for row in subset if accepted(row))}/{len(subset)} | "
            f"{sum(row['wall_seconds'] for row in subset):.1f} | {walls[len(walls) // 2]:.1f} | "
            f"{sum(row['usage']['total'] for row in subset)} | "
            f"{sum(row['usage']['input'] for row in subset)} | "
            f"{sum(row['usage']['output'] for row in subset)} | "
            f"${sum(row['usage']['cost_usd'] for row in subset):.4f} | "
            f"{sum(1 for row in subset if not row['scope_ok'])} | "
            f"{sum(1 for row in subset if row['timed_out'])} |"
        )
    lines.append("")

    lines.append("## Same-model pairing (Pi minus OMP)")
    lines.append("")
    lines.append("| Model | Thinking | Task | Acceptance (Pi/OMP) | Wall s (Pi/OMP) | "
                 "Tokens (Pi/OMP) | Cost (Pi/OMP) |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for model in sorted({row["model_short"] for row in rows}):
        for thinking in sorted({row["thinking"] for row in rows}):
            for task in sorted({row["task"] for row in rows}):
                pair = {row["arm"]: row for row in rows
                        if (row["model_short"], row["thinking"], row["task"]) == (model, thinking, task)}
                if set(pair) != {"pi", "omp"}:
                    continue
                pi_row, omp_row = pair["pi"], pair["omp"]
                lines.append(
                    f"| {model} | {thinking} | {task} | "
                    f"{'P' if accepted(pi_row) else 'F'}/{'P' if accepted(omp_row) else 'F'} | "
                    f"{pi_row['wall_seconds']:.1f}/{omp_row['wall_seconds']:.1f} | "
                    f"{pi_row['usage']['total']}/{omp_row['usage']['total']} | "
                    f"${pi_row['usage']['cost_usd']:.4f}/${omp_row['usage']['cost_usd']:.4f} |"
                )
    lines.append("")

    text = "\n".join(lines) + "\n"
    if args.out:
        out_path = Path(args.out).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text)
        (out_path.parent / "trials.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(target):
        target.add_argument("--baseline", required=True, help="clean MEGAI checkout at the frozen SHA")
        target.add_argument("--root", required=True, help="private evidence directory outside the repo")
        target.add_argument("--results", required=True, help="results.jsonl path")
        target.add_argument("--budget", type=int, default=BUDGET_SECONDS)

    trial = sub.add_parser("trial")
    add_common(trial)
    trial.add_argument("--arm", required=True, choices=ARMS)
    trial.add_argument("--model", required=True, choices=MODELS)
    trial.add_argument("--thinking", required=True, choices=THINKING_LEVELS)
    trial.add_argument("--task", required=True, choices=tuple(TASK_IMPL))
    trial.set_defaults(func=cmd_trial)

    matrix = sub.add_parser("matrix")
    add_common(matrix)
    matrix.add_argument("--arms")
    matrix.add_argument("--models")
    matrix.add_argument("--thinkings")
    matrix.add_argument("--tasks")
    matrix.set_defaults(func=cmd_matrix)

    overhead = sub.add_parser("overhead")
    overhead.add_argument("--root", required=True)
    overhead.add_argument("--cwd", required=True, help="neutral checkout both arms start in")
    overhead.add_argument("--model", default="deepseek/deepseek-flash")
    overhead.add_argument("--arms")
    overhead.add_argument("--reps", type=int, default=3)
    overhead.set_defaults(func=cmd_overhead)

    summary = sub.add_parser("summarize")
    summary.add_argument("--results", required=True)
    summary.add_argument("--root", required=True)
    summary.add_argument("--out")
    summary.set_defaults(func=cmd_summarize)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
