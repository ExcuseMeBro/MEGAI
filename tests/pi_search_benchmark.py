#!/usr/bin/env python3
"""Explicit disposable indexed-search check; timings never assert a speedup."""
import json
import math
from pathlib import Path
import statistics
import subprocess
import tempfile
import time


def run(root, argv):
    start = time.perf_counter()
    result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=60)
    elapsed = (time.perf_counter() - start) * 1000
    assert result.returncode == 0, (argv, result.returncode, result.stderr)
    return result, elapsed


def main():
    with tempfile.TemporaryDirectory(prefix="megai-tgrep-scenario-") as folder:
        root = Path(folder)
        run(root, ["git", "init", "-q", "."])
        for number in range(400):
            body = "".join(
                f'export const value_{number}_{line} = "ordinary service configuration {number}";\n'
                for line in range(256)
            )
            if number in (17, 193, 307):
                body += 'export const payment_retry_marker = "selected";\n'
            (root / f"module_{number:03}.ts").write_text(body)
        _, build_ms = run(root, ["tgrep", "index", "."])
        assert (root / ".tgrep").is_dir()
        cases = [
            ["-F", "payment_retry_marker"],
            ["payment_.*_marker"],
            ["-i", "-F", "PAYMENT_RETRY_MARKER"],
        ]
        timings = {}
        for arguments in cases:
            results = {}
            for tool in ("tgrep", "rg"):
                samples = []
                for _ in range(5):
                    result, elapsed = run(root, [tool, "-n", "--color", "never", *arguments, "."])
                    matches = sorted(result.stdout.splitlines())
                    assert len(matches) == 3, (tool, arguments, matches)
                    assert {line.split(":", 1)[0] for line in matches} == {
                        "./module_017.ts", "./module_193.ts", "./module_307.ts"
                    }
                    results[tool] = matches
                    samples.append(round(elapsed, 2))
                timings.setdefault(" ".join(arguments), {})[tool] = samples
            assert results["tgrep"] == results["rg"], arguments
        # An edited tree uses native evidence, never index status as freshness proof.
        changed = root / "module_000.ts"
        changed.write_text(changed.read_text() + "// fresh_native_only_marker\n")
        result, _ = run(root, ["rg", "-n", "-F", "fresh_native_only_marker", "."])
        assert "module_000.ts:257:" in result.stdout
        literal = timings["-F payment_retry_marker"]
        indexed_ms = statistics.median(literal["tgrep"])
        native_ms = statistics.median(literal["rg"])
        difference = native_ms - indexed_ms
        print(json.dumps({
            "fixture": "400 disposable text files; literal, regex and case-insensitive matches equal native rg",
            "indexBuildMs": round(build_ms, 2), "samplesMs": timings,
            "literalMedianMs": {"tgrep": indexed_ms, "rg": native_ms},
            "estimatedBreakEvenQueries": math.ceil(build_ms / difference) if difference > 0 else None,
            "afterEdit": "native rg found new source; no stale index used as evidence",
            "scope": "local CLI timings only; no server, universal speedup or token claim",
        }, indent=2))


if __name__ == "__main__":
    main()
