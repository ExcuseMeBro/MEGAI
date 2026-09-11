"""Render check results; both supported formats are compatibility surfaces."""

import json


def render_checks(checks: list[tuple[str, str]], style: str = "text") -> str:
    if style == "text":
        passed = 0
        failed = 0
        skipped = 0
        lines = []
        for name, status in checks:
            if status == "pass":
                passed += 1
            elif status == "fail":
                failed += 1
            elif status == "skip":
                skipped += 1
            else:
                raise ValueError("unknown status")
            lines.append(f"{status.upper()} {name}")
        lines.append(
            f"TOTAL {len(checks)} | PASS {passed} | FAIL {failed} | SKIP {skipped}"
        )
        return "\n".join(lines)
    if style == "json":
        passed = 0
        failed = 0
        skipped = 0
        records = []
        for name, status in checks:
            if status == "pass":
                passed += 1
            elif status == "fail":
                failed += 1
            elif status == "skip":
                skipped += 1
            else:
                raise ValueError("unknown status")
            records.append({"name": name, "status": status})
        return json.dumps(
            {
                "total": len(checks),
                "pass": passed,
                "fail": failed,
                "skip": skipped,
                "checks": records,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    raise ValueError("unknown style")
