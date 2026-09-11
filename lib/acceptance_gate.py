#!/usr/bin/env python3
"""Fail-closed local acceptance evidence gate.

Snapshots cover Git HEAD, index entries and all tracked/nonignored regular files;
ignored build outputs are intentionally excluded.  ``run`` executes an argv
without a shell and is neither a watchdog nor a sandbox: callers choose bounded
checks and this helper never kills an in-flight command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import time
import uuid

APPROVED_MODELS = {
    "openai-codex/gpt-5.6-luna",
    "openai-codex/gpt-5.6-terra",
    "openai-codex/gpt-5.6-sol",
    "openai-codex/gpt-6-astra",
}
SHA256_LENGTH = 64


class GateError(Exception):
    """An input or safety violation which must fail closed."""


def _git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], stderr=subprocess.PIPE
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise GateError("Git operation unavailable") from exc


def _repo_root(root: Path) -> Path:
    try:
        supplied = root.resolve(strict=True)
        top = Path(
            _git(supplied, "rev-parse", "--show-toplevel").strip().decode()
        ).resolve(strict=True)
    except (OSError, UnicodeDecodeError) as exc:
        raise GateError("Repository root unavailable") from exc
    if supplied != top:
        raise GateError("Root must be the Git top-level directory")
    return top


def _parts(raw: bytes) -> list[str]:
    return [
        part.decode("utf-8", "surrogateescape") for part in raw.split(b"\0") if part
    ]


def _frame(digest, label: bytes, value: bytes) -> None:
    digest.update(label)
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def _source_path(root: Path, relative: str) -> Path:
    path = root / relative
    current = root
    for part in Path(relative).parts:
        current = current / part
        try:
            mode = os.lstat(current).st_mode
        except FileNotFoundError:
            return path
        except OSError as exc:
            raise GateError("Source path unreadable") from exc
        if stat.S_ISLNK(mode):
            raise GateError("Symlink source path rejected")
    return path


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise GateError("File unreadable") from exc
    return digest.hexdigest(), size


def snapshot(root: Path) -> str:
    """Return a framed, deterministic fingerprint of the complete repository."""
    root = _repo_root(root)
    if _git(root, "ls-files", "-u", "-z"):
        raise GateError("Unresolved Git conflicts")
    index = _git(root, "ls-files", "-s", "-z")
    for entry in _parts(index):
        if entry.startswith("160000 "):
            raise GateError("Submodule rejected")
    tracked = set(_parts(_git(root, "ls-files", "-z")))
    untracked = set(
        _parts(_git(root, "ls-files", "--others", "--exclude-standard", "-z"))
    )
    digest = hashlib.sha256()
    head = _git(root, "rev-parse", "HEAD").strip()
    _frame(digest, b"head", head)
    _frame(digest, b"index", index)
    observed = {}
    for relative in sorted(tracked | untracked):
        path = _source_path(root, relative)
        try:
            source_stat = os.lstat(path)
        except FileNotFoundError:
            if relative not in tracked:
                raise GateError("Untracked source disappeared")
            _frame(digest, b"deleted", relative.encode("utf-8", "surrogateescape"))
            observed[relative] = None
            continue
        except OSError as exc:
            raise GateError("Source path unreadable") from exc
        if not stat.S_ISREG(source_stat.st_mode):
            raise GateError("Nonregular source path rejected")
        observed[relative] = source_stat
        content_hash, size = _file_sha256(path)
        _frame(digest, b"path", relative.encode("utf-8", "surrogateescape"))
        _frame(digest, b"mode", str(stat.S_IMODE(source_stat.st_mode)).encode())
        _frame(digest, b"size", str(size).encode())
        _frame(digest, b"sha256", content_hash.encode())
    if (
        _git(root, "rev-parse", "HEAD").strip() != head
        or _git(root, "ls-files", "-s", "-z") != index
        or set(_parts(_git(root, "ls-files", "-z"))) != tracked
        or set(_parts(_git(root, "ls-files", "--others", "--exclude-standard", "-z")))
        != untracked
    ):
        raise GateError("Source inventory changed during snapshot")
    for relative, before in observed.items():
        path = _source_path(root, relative)
        try:
            after = os.lstat(path)
        except FileNotFoundError:
            after = None
        if before is None or after is None:
            stable = before is after
        else:
            stable = all(
                getattr(before, field) == getattr(after, field)
                for field in ("st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
            )
        if not stable:
            raise GateError("Source changed during snapshot")
    return digest.hexdigest()


def _is_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_schema_one(value: object) -> bool:
    return _is_int(value) and value == 1


def _json_file(path: Path) -> object:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in items:
            if key in output:
                raise GateError("Duplicate JSON key")
            output[key] = value
        return output

    def constant(_: str) -> object:
        raise GateError("Non-finite JSON number")

    try:
        return json.loads(
            path.read_bytes(), object_pairs_hook=pairs, parse_constant=constant
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GateError("Malformed JSON or unreadable file") from exc


def _no_symlink_ancestors(path: Path) -> None:
    current = Path(path.absolute().anchor)
    for part in path.absolute().parts[1:]:
        current /= part
        try:
            is_link = stat.S_ISLNK(os.lstat(current).st_mode)
        except FileNotFoundError:
            break
        if is_link and str(current) not in {"/var", "/tmp"}:
            raise GateError("Symlink ancestor rejected")


def _external_regular(path: Path, root: Path) -> Path:
    _no_symlink_ancestors(path)
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except ValueError:
        pass
    except OSError as exc:
        raise GateError("External file unavailable") from exc
    else:
        raise GateError("Evidence must be outside repository")
    try:
        if path.is_symlink() or not stat.S_ISREG(os.lstat(path).st_mode):
            raise GateError("Evidence must be a regular non-symlink file")
    except OSError as exc:
        raise GateError("External file unavailable") from exc
    return resolved


def _relative(base: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise GateError("Artifact path must be nonempty")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError("Unsafe artifact path")
    current = base
    for part in relative.parts:
        current = current / part
        try:
            if stat.S_ISLNK(os.lstat(current).st_mode):
                raise GateError("Artifact symlink rejected")
        except FileNotFoundError:
            raise GateError("Artifact missing") from None
        except OSError as exc:
            raise GateError("Artifact unavailable") from exc
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(base.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise GateError("Artifact path escapes evidence directory") from exc
    if not stat.S_ISREG(os.lstat(current).st_mode):
        raise GateError("Artifact must be regular")
    return resolved


def _artifact(base: Path, value: object) -> None:
    if not isinstance(value, dict) or set(value) != {"path", "sha256"}:
        raise GateError("Malformed artifact")
    if not _is_hash(value.get("sha256")):
        raise GateError("Invalid artifact hash")
    path = _relative(base, value.get("path"))
    if _file_sha256(path)[0] != value["sha256"]:
        raise GateError("Artifact hash mismatch")


def _contract(value: object) -> dict[str, object]:
    keys = {"schema", "plane", "implementer_session_id", "runtime", "criteria"}
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or not _is_schema_one(value["schema"])
    ):
        raise GateError("Unsupported contract schema")
    plane = value["plane"]
    if not isinstance(plane, dict) or set(plane) != {"project_id", "work_item_id"}:
        raise GateError("Malformed contract plane")
    for name in ("project_id", "work_item_id"):
        try:
            if not isinstance(plane[name], str):
                raise ValueError
            uuid.UUID(plane[name])
        except (ValueError, AttributeError):
            raise GateError("Invalid contract UUID") from None
    if (
        not isinstance(value["implementer_session_id"], str)
        or not value["implementer_session_id"].strip()
    ):
        raise GateError("Missing implementer session")
    runtime = value["runtime"]
    runtime_keys = {"required", "authorized", "environment", "targets", "reason"}
    if not isinstance(runtime, dict) or set(runtime) != runtime_keys:
        raise GateError("Malformed runtime")
    environment = runtime["environment"]
    if (
        not isinstance(runtime["required"], bool)
        or not isinstance(runtime["authorized"], bool)
        or not isinstance(environment, str)
        or environment not in {"local", "staging", "none"}
        or not isinstance(runtime["targets"], list)
        or not all(isinstance(target, str) and target for target in runtime["targets"])
        or not isinstance(runtime["reason"], str)
    ):
        raise GateError("Malformed runtime values")
    if runtime["required"]:
        if not runtime["authorized"] or environment == "none" or not runtime["targets"]:
            raise GateError("Unauthorized runtime")
    elif runtime["targets"] or not runtime["reason"]:
        raise GateError("Invalid non-runtime contract")
    criteria = value["criteria"]
    if not isinstance(criteria, list) or not criteria:
        raise GateError("Missing criteria")
    ids: set[str] = set()
    runtime_count = 0
    for criterion in criteria:
        allowed = {"id", "kind", "expected", "command", "target"}
        required = {"id", "kind", "expected", "command"}
        if (
            not isinstance(criterion, dict)
            or not required <= set(criterion)
            or set(criterion) - allowed
        ):
            raise GateError("Malformed criterion")
        identifier = criterion["id"]
        kind = criterion["kind"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in ids
            or not isinstance(kind, str)
            or kind not in {"test", "runtime"}
            or not isinstance(criterion["expected"], str)
            or not criterion["expected"]
            or not isinstance(criterion["command"], list)
            or not criterion["command"]
            or not all(isinstance(arg, str) and arg for arg in criterion["command"])
        ):
            raise GateError("Invalid criterion")
        ids.add(identifier)
        if kind == "runtime":
            runtime_count += 1
            if criterion.get("target") not in runtime["targets"]:
                raise GateError("Invalid runtime target")
        elif "target" in criterion:
            raise GateError("Test criterion target forbidden")
    if bool(runtime_count) != runtime["required"]:
        raise GateError("Runtime criteria mismatch")
    return value


def _receipt(value: object, command: object, snapshot_value: str, root: Path) -> int:
    keys = {
        "schema",
        "argv",
        "cwd",
        "snapshot_before",
        "snapshot_after",
        "exit_code",
        "duration_seconds",
        "log",
    }
    if (
        not isinstance(value, dict)
        or set(value) != keys
        or not _is_schema_one(value["schema"])
    ):
        raise GateError("Malformed receipt")
    if value["argv"] != command or value["cwd"] != str(root):
        raise GateError("Receipt command or cwd mismatch")
    if (
        value["snapshot_before"] != snapshot_value
        or value["snapshot_after"] != snapshot_value
    ):
        raise GateError("Receipt snapshot mismatch")
    duration = value["duration_seconds"]
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(duration)
        or duration < 0
    ):
        raise GateError("Invalid receipt duration")
    code = value["exit_code"]
    if code is None:
        raise GateError("Executable unavailable")
    if not _is_int(code):
        raise GateError("Invalid receipt exit code")
    return code


def check(
    contract_file: Path, approved: str, evidence_file: Path, root_arg: Path
) -> tuple[str, list[str]]:
    try:
        root = _repo_root(root_arg)
        contract_path = _external_regular(contract_file, root)
        evidence_path = _external_regular(evidence_file, root)
        if not _is_hash(approved) or _file_sha256(contract_path)[0] != approved:
            raise GateError("Contract hash mismatch")
        contract = _contract(_json_file(contract_path))
        evidence = _json_file(evidence_path)
        evidence_keys = {"schema", "contract_sha256", "snapshot", "checks", "review"}
        if (
            not isinstance(evidence, dict)
            or set(evidence) != evidence_keys
            or not _is_schema_one(evidence["schema"])
        ):
            raise GateError("Malformed evidence")
        current = snapshot(root)
        if evidence["contract_sha256"] != approved or evidence["snapshot"] != current:
            raise GateError("Evidence snapshot mismatch")
        if not isinstance(evidence["checks"], list):
            raise GateError("Malformed checks")
        criteria = {item["id"]: item for item in contract["criteria"]}
        seen: set[str] = set()
        result = "PASS"
        base = evidence_path.parent
        for item in evidence["checks"]:
            required = {"id", "status", "observation", "receipt", "artifacts"}
            if not isinstance(item, dict) or set(item) != required:
                raise GateError("Malformed check")
            identifier = item["id"]
            status_value = item["status"]
            if (
                not isinstance(identifier, str)
                or identifier not in criteria
                or identifier in seen
            ):
                raise GateError("Missing or duplicate criterion evidence")
            if not isinstance(status_value, str) or status_value not in {
                "PASS",
                "FAIL",
                "BLOCKED",
            }:
                raise GateError("Invalid check status")
            if (
                not isinstance(item["observation"], str)
                or not item["observation"].strip()
            ):
                raise GateError("Missing check observation")
            if not isinstance(item["artifacts"], list):
                raise GateError("Malformed check artifacts")
            seen.add(identifier)
            receipt_path = _relative(base, item["receipt"])
            receipt = _json_file(receipt_path)
            code = _receipt(receipt, criteria[identifier]["command"], current, root)
            _artifact(receipt_path.parent, receipt["log"])
            for artifact in item["artifacts"]:
                _artifact(base, artifact)
            if status_value == "BLOCKED":
                raise GateError("Check declared BLOCKED")
            if status_value == "FAIL" or code != 0:
                result = "FAIL"
        if seen != set(criteria):
            raise GateError("Missing criterion evidence")
        review = evidence["review"]
        review_keys = {
            "session_id",
            "harness",
            "model",
            "thinking",
            "verdict",
            "snapshot",
            "contract_sha256",
            "criteria",
            "artifact",
        }
        if not isinstance(review, dict) or set(review) != review_keys:
            raise GateError("Malformed review")
        if (
            not isinstance(review["session_id"], str)
            or not review["session_id"]
            or review["session_id"] == contract["implementer_session_id"]
            or review["harness"] != "pi"
            or not isinstance(review["model"], str)
            or review["model"] not in APPROVED_MODELS
            or review["thinking"] != "high"
            or review["snapshot"] != current
            or review["contract_sha256"] != approved
            or not isinstance(review["criteria"], list)
            or not all(isinstance(item, str) for item in review["criteria"])
            or set(review["criteria"]) != set(criteria)
            or len(review["criteria"]) != len(criteria)
        ):
            raise GateError("Invalid independent review")
        if not isinstance(review["verdict"], str) or review["verdict"] not in {
            "PASS",
            "FAIL",
            "BLOCKED",
        }:
            raise GateError("Invalid review verdict")
        _artifact(base, review["artifact"])
        if review["verdict"] == "BLOCKED":
            raise GateError("Review declared BLOCKED")
        if review["verdict"] == "FAIL":
            result = "FAIL"
        return result, []
    except GateError as exc:
        return "BLOCKED", [str(exc)]
    except Exception:
        return "BLOCKED", ["Unexpected validation failure"]


def _safe_out(root: Path, output: Path) -> Path:
    raw = output.absolute()
    _no_symlink_ancestors(raw)
    try:
        resolved = raw.resolve(strict=False)
        resolved.relative_to(root)
    except ValueError:
        pass
    except OSError as exc:
        raise GateError("Output path unavailable") from exc
    else:
        raise GateError("Output directory must be outside repository")
    try:
        if raw.exists() or raw.is_symlink() or not raw.parent.is_dir():
            raise GateError("Output destination must be new with an existing parent")
    except OSError as exc:
        raise GateError("Output path unavailable") from exc
    return raw


def _write_receipt(path: Path, value: dict[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, allow_nan=False)


def run(root_arg: Path, output: Path, argv: list[str]) -> tuple[str, int]:
    try:
        root = _repo_root(root_arg)
        before = snapshot(root)
        output = _safe_out(root, output)
        os.mkdir(output, 0o700)
    except (GateError, OSError) as exc:
        print(json.dumps({"status": "BLOCKED", "reasons": [str(exc)]}))
        return "BLOCKED", 2
    log_path = output / "output.txt"
    started = time.monotonic()
    descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as log:
        try:
            code: int | None = subprocess.Popen(
                argv, cwd=root, stdout=log, stderr=subprocess.STDOUT, shell=False
            ).wait()
        except FileNotFoundError as exc:
            log.write(f"{exc}\n".encode())
            code = None
        except (OSError, ValueError) as exc:
            log.write(f"{exc}\n".encode())
            code = None
    try:
        after = snapshot(root)
        reason = "Source changed during command" if after != before else ""
    except GateError as exc:
        after = None
        reason = str(exc)
    receipt = {
        "schema": 1,
        "argv": argv,
        "cwd": str(root),
        "snapshot_before": before,
        "snapshot_after": after,
        "exit_code": code,
        "duration_seconds": time.monotonic() - started,
        "log": {"path": "output.txt", "sha256": _file_sha256(log_path)[0]},
    }
    try:
        _write_receipt(output / "receipt.json", receipt)
    except OSError as exc:
        print(json.dumps({"status": "BLOCKED", "reasons": [str(exc)]}))
        return "BLOCKED", 2
    if code is None and not reason:
        reason = "Executable unavailable; inspect raw output.txt"
    if code == 0 and not reason:
        status, exit_code = "PASS", 0
    elif code is not None and not reason:
        status, exit_code = "FAIL", 1
    else:
        status, exit_code = "BLOCKED", 2
    print(
        json.dumps(
            {
                "status": status,
                "reasons": [reason] if reason else [],
                "receipt": str(output / "receipt.json"),
            }
        )
    )
    return status, exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--root", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--root", required=True)
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("argv", nargs=argparse.REMAINDER)
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument("--root", required=True)
    check_parser.add_argument("--contract", required=True)
    check_parser.add_argument("--contract-sha256", required=True)
    check_parser.add_argument("--evidence", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    if args.action == "snapshot":
        try:
            print(json.dumps({"snapshot": snapshot(root)}))
            return 0
        except GateError as exc:
            print(json.dumps({"status": "BLOCKED", "reasons": [str(exc)]}))
            return 2
    if args.action == "run":
        argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        if not argv:
            print(json.dumps({"status": "BLOCKED", "reasons": ["Missing command"]}))
            return 2
        return run(root, Path(args.out), argv)[1]
    status, reasons = check(
        Path(args.contract), args.contract_sha256, Path(args.evidence), root
    )
    print(json.dumps({"status": status, "reasons": reasons}))
    return {"PASS": 0, "FAIL": 1, "BLOCKED": 2}[status]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (GateError, OSError, ValueError, RuntimeError) as error:
        print(json.dumps({"status": "BLOCKED", "reasons": [str(error)]}))
        raise SystemExit(2) from None
