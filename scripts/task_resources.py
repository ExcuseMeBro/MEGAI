#!/usr/bin/env python3
"""Explicit local, label-scoped Docker/process/cache cleanup after verified delivery."""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path

PREFIX = "io.megai."
KINDS = ("container", "network", "volume", "image")
TASK = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}")
IDENTITY = re.compile(r"[0-9a-f]{64}")
ANONYMOUS_VOLUME = re.compile(r"[0-9a-f]{64}")
GRADLE_VERSION = re.compile(r"\d+\.\d+(?:\.\d+)*")
GRADLE_DISTRIBUTION = re.compile(r"gradle-(\d+\.\d+(?:\.\d+)*)-(?:bin|all)\.zip")
GRADLE_DIST_DIR = re.compile(r"gradle-(\d+\.\d+(?:\.\d+)*)-(?:bin|all)")
STATE = Path.home() / ".local/state/megai-task-resources/registry.json"


class Refused(RuntimeError):
    pass


def run(argv, env=None):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=90, env=env,
                            check=False)
    if result.returncode:
        # Avoid echoing subprocess output (container metadata may contain secrets).
        raise Refused(f"Command failed ({result.returncode}): {argv[0]} {argv[1]}")
    return result.stdout.strip()


def git(repo, *args):
    return run(["git", "-C", str(repo), *args])


def repo_common(repo):
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).resolve()


def repo_identity(repo):
    return hashlib.sha256(str(repo_common(repo)).encode()).hexdigest()


def labels(repo, task):
    if not TASK.fullmatch(task):
        raise Refused("Task must be a unique lowercase slug (1-80 characters)")
    return {PREFIX + "repo": repo_identity(repo), PREFIX + "task": task,
            PREFIX + "disposable": "true"}


def owned(metadata, expected):
    return isinstance(metadata, dict) and all(metadata.get(k) == v for k, v in expected.items())


def verify_delivery(repo, commit, remote):
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise Refused("Use the full delivered commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", remote):
        raise Refused("Invalid remote name")
    if not git(repo, "symbolic-ref", "--short", "HEAD").startswith("task/"):
        raise Refused("Run before removing the task worktree, on its task/ branch")
    if git(repo, "status", "--porcelain", "--untracked-files=normal"):
        raise Refused("Task worktree has uncommitted changes")
    if git(repo, "rev-parse", "HEAD") != commit:
        raise Refused("Commit must equal the task worktree HEAD")
    # Explicit refspec prevents trusting a stale remote-tracking ref or custom fetch config.
    git(repo, "fetch", "--no-tags", remote, f"refs/heads/dev:refs/remotes/{remote}/dev")
    git(repo, "merge-base", "--is-ancestor", commit, f"refs/remotes/{remote}/dev")


class Docker:
    def __init__(self, context):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", context):
            raise Refused("Invalid Docker context")
        self.context = context
        self.env = {k: v for k, v in os.environ.items()
                    if k not in {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}}
        contexts = json.loads(run(["docker", "context", "inspect", context], self.env))
        endpoint = contexts[0]["Endpoints"]["docker"]["Host"]
        if not endpoint.startswith("unix:///"):
            raise Refused("Cleanup supports explicit local Unix-socket contexts only")
        # Pin the endpoint, not the mutable context name, for this invocation.
        self.base = ["docker", "--host", endpoint]
        self.kiri_store = (Path.home() / "Library/Application Support/kiri"
                           if endpoint == "unix://" + str(Path.home() / ".kiri/run/docker.sock") else None)
        self.call("version", "--format", "{{.Server.Version}}")

    def call(self, *args):
        return run([*self.base, *args], self.env)

    def inspect(self, kind, identity):
        data = json.loads(self.call(kind, "inspect", identity))
        if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
            raise Refused("Unexpected inspect response")
        item = data[0]
        if item.get("Config") is not None and not isinstance(item["Config"], dict):
            raise Refused("Unexpected resource config")
        if kind == "image" and self.kiri_store and "Labels" not in (item.get("Config") or {}):
            # Kiri omits image labels from both Docker list and inspect responses.
            # Read only the content-addressed config, verify its digest, never
            # infer ownership from a tag and never modify Kiri's internal store.
            item.setdefault("Config", {})["Labels"] = kiri_image_labels(self.kiri_store, canonical(kind, item))
        return item

    def candidates(self, kind, expected):
        args = [kind, "ls", "--quiet"]
        if kind in ("container", "image"):
            args += ["--all", "--no-trunc"]
        if kind != "image" or not self.kiri_store:
            for key, value in expected.items():
                args += ["--filter", f"label={key}={value}"]
        return sorted(set(self.call(*args).split()))

    def everything(self, kind):
        """All identities of a kind; label checks stay client-side."""
        args = [kind, "ls", "--quiet"]
        if kind in ("container", "image"):
            args += ["--all", "--no-trunc"]
        return sorted(set(self.call(*args).split()))


def kiri_image_labels(store, identity):
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", identity):
        raise Refused("Invalid Kiri config digest")
    path = store / "blobs/sha256" / identity[7:]
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise Refused("Kiri image config is not a regular file")
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != identity[7:]:
        raise Refused("Kiri config size/digest validation failed")
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("config"), dict):
        raise Refused("Invalid Kiri image config")
    return data["config"].get("Labels")


def metadata(kind, item):
    if kind in ("container", "image"):
        return (item.get("Config") or {}).get("Labels")
    return item.get("Labels")


def canonical(kind, item):
    key = "Name" if kind == "volume" else "Id"
    value = item.get(key)
    pattern = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}" if kind == "volume" else r"(?:sha256:)?[0-9a-f]{64}"
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise Refused("Invalid resource identity")
    return value


UTC = datetime.timezone.utc  # noqa: UP017 - the installed helper runs on system python3 3.9
FRACTION = re.compile(r"^(.*\.\d{6})\d*(.*)$")


def timestamp(value):
    """Parse Docker's RFC3339 stamp under Python 3.9+ (no `Z`, nanosecond support)."""
    text = str(value).strip()
    if text[-1:] in {"Z", "z"}:
        text = text[:-1] + "+00:00"
    trimmed = FRACTION.match(text)
    if trimmed:
        text = trimmed.group(1) + trimmed.group(2)
    stamp = datetime.datetime.fromisoformat(text)
    return stamp if stamp.tzinfo is not None else stamp.replace(tzinfo=UTC)


def age_hours(value):
    """Docker's RFC3339 creation stamp as an age; unknown or future means too recent."""
    try:
        stamp = timestamp(value)
    except (TypeError, ValueError):
        return 0.0

    age = (datetime.datetime.now(UTC) - stamp).total_seconds() / 3600
    return age if age > 0 else 0.0


def elapsed_hours(text):
    days = 0
    if "-" in text:
        head, text = text.split("-", 1)
        days = int(head)
    parts = [int(p) for p in text.split(":")]
    if len(parts) == 2:
        parts = [0, *parts]
    hours, minutes, seconds = parts
    return days * 24 + hours + minutes / 60 + seconds / 3600


def drop(docker, kind, identity, eligible, apply, emit=print):
    """Remove one resource, re-verifying eligibility and never forcing."""
    if not apply:
        emit(json.dumps({"action": "preview", "kind": kind, "id": identity}))
        return False
    item = docker.inspect(kind, identity)
    if canonical(kind, item) != identity or not eligible(item):
        raise Refused("Resource eligibility changed; refusing removal")
    if kind == "container":
        if (item.get("State") or {}).get("Running"):
            docker.call("container", "stop", "--time", "10", identity)
        # No force, no -v: anonymous volumes are not implicitly disposable.
        docker.call("container", "rm", identity)
    elif kind == "network":
        if item.get("Containers"):
            raise Refused("Network still has attached containers; refusing removal")
        docker.call("network", "rm", identity)
    else:
        # Engine rejects in-use volumes/images; never force deletion or prune.
        docker.call(kind, "rm", identity)
    emit(json.dumps({"action": "remove", "kind": kind, "id": identity}))
    return True


def cleanup(docker, expected, apply=False, emit=print):
    plan = []
    # Inspect ALL candidates before any mutation. Filters alone are not trusted.
    for kind in KINDS:
        for candidate in docker.candidates(kind, expected):
            item = docker.inspect(kind, candidate)
            if owned(metadata(kind, item), expected):
                plan.append((kind, canonical(kind, item)))
    for kind, identity in plan:
        drop(docker, kind, identity,
             lambda item, kind=kind: owned(metadata(kind, item), expected), apply, emit)
    return plan


# --- repository/state registry -------------------------------------------------

def load_registry(path=STATE):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, dict):
        return {}
    return {k: v for k, v in repos.items()
            if isinstance(k, str) and IDENTITY.fullmatch(k) and isinstance(v, str) and v.startswith("/")}


def remember(repo, task, path=STATE):
    """Map a repo identity hash back to its common dir so later sweeps can verify it."""
    identity = repo_identity(repo)
    repos = load_registry(path)
    repos[identity] = str(repo_common(repo))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps({"version": 1, "repos": repos}, sort_keys=True))
    temp.chmod(0o600)
    os.replace(temp, path)
    return identity


def resolve_repo(identity, hints=(), path=STATE):
    """Only return a path that still hashes to this identity."""
    candidates = [Path(p) for p in hints]
    known = load_registry(path).get(identity)
    if known:
        candidates.append(Path(known))
    for candidate in candidates:
        try:
            if repo_identity(candidate) == identity:
                return candidate
        except (Refused, OSError, subprocess.TimeoutExpired):
            continue
    return None


def task_inactive(repo, task):
    """True only when no task branch and no worktree for it remain."""
    branch = f"refs/heads/task/{task}"
    verify = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", branch],
                            text=True, capture_output=True, timeout=60, check=False)
    if verify.returncode == 0:
        return False
    if verify.returncode != 1:
        raise Refused("Cannot inspect task branch state")
    for line in git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.strip() == f"branch {branch}":
            return False
    return True


# --- sweep: orphaned labelled resources, anonymous volumes, temp clusters ------

def volume_references(docker):
    names = set()
    for identity in docker.everything("container"):
        item = docker.inspect("container", identity)
        for mount in item.get("Mounts") or []:
            if isinstance(mount, dict) and mount.get("Type") == "volume" and isinstance(mount.get("Name"), str):
                names.add(mount["Name"])
    return names


def sweep(docker, hints=(), anonymous=False, apply=False, min_age_hours=24.0, emit=print):
    """Remove labelled groups whose repo is verifiable and whose task is finished."""
    groups = {}
    for kind in KINDS:
        for identity in docker.everything(kind):
            item = docker.inspect(kind, identity)
            meta = metadata(kind, item)
            if not isinstance(meta, dict) or meta.get(PREFIX + "disposable") != "true":
                continue
            repo_id, task = meta.get(PREFIX + "repo"), meta.get(PREFIX + "task")
            if not isinstance(repo_id, str) or not IDENTITY.fullmatch(repo_id) \
                    or not isinstance(task, str) or not TASK.fullmatch(task):
                emit(json.dumps({"action": "skip", "kind": kind, "id": canonical(kind, item),
                                 "reason": "invalid-labels"}))
                continue
            when = item.get("Created", item.get("CreatedAt"))
            groups.setdefault((repo_id, task), []).append((kind, canonical(kind, item), when))

    for (repo_id, task) in sorted(groups):
        entries = groups[(repo_id, task)]
        order = {kind: index for index, kind in enumerate(KINDS)}
        entries.sort(key=lambda entry: (order[entry[0]], entry[1]))
        reject = None
        repo = resolve_repo(repo_id, hints)
        if repo is None:
            reject = "repo-unresolved"
        else:
            try:
                if labels(repo, task)[PREFIX + "repo"] != repo_id:
                    reject = "repo-mismatch"
                elif not task_inactive(repo, task):
                    reject = "task-branch-active"
                elif min(age_hours(when) for _, _, when in entries) < min_age_hours:
                    reject = "too-recent"
            except (Refused, OSError, subprocess.TimeoutExpired) as exc:
                reject = f"unverifiable: {exc}"
        if reject:
            for kind, identity, _ in entries:
                emit(json.dumps({"action": "skip", "kind": kind, "id": identity, "task": task,
                                 "repo": repo_id, "reason": reject}))
            continue
        for kind, identity, _ in entries:
            drop(docker, kind, identity,
                 lambda item, kind=kind, repo_id=repo_id, task=task: owned(
                     metadata(kind, item), {PREFIX + "repo": repo_id, PREFIX + "task": task,
                                            PREFIX + "disposable": "true"}),
                 apply, emit)

    if anonymous:
        referenced = volume_references(docker)
        for identity in docker.everything("volume"):
            item = docker.inspect("volume", identity)
            name = canonical("volume", item)
            if not ANONYMOUS_VOLUME.fullmatch(name) or name in referenced:
                continue
            if any(str(key).startswith(PREFIX) for key in (item.get("Labels") or {})):
                continue
            if age_hours(item.get("CreatedAt")) < min_age_hours:
                continue
            drop(docker, "volume", name,
                 lambda item, name=name: (
                     canonical("volume", item) == name
                     and not any(str(k).startswith(PREFIX) for k in (item.get("Labels") or {}))
                     and name not in volume_references(docker)),
                 apply, emit)


def temp_roots():
    roots = {Path("/tmp").resolve()}
    if Path("/private/tmp").exists():
        roots.add(Path("/private/tmp").resolve())
    temp = os.environ.get("TMPDIR")
    if temp:
        try:
            roots.add(Path(temp).resolve())
        except OSError:
            pass
    return {root for root in roots if root.is_dir()}


def temp_clusters(roots, min_age_hours=24.0):
    """Orphaned (parent gone) PostgreSQL servers whose data dir sits in temp."""
    found = []
    for line in run(["ps", "-axo", "pid=,ppid=,etime=,command="]).splitlines():
        fields = line.split(None, 3)
        if len(fields) != 4:
            continue
        pid, ppid, elapsed, command = fields
        if not re.search(r"(?:^|/)postgres ", command) or " -D " not in command:
            continue
        match = re.search(r" -D (\S+)", command)
        if not match:
            continue
        try:
            data = Path(match.group(1)).resolve(strict=True)
        except OSError:
            continue
        if data.name in ("", ".", "..") or not any(
                data != root and data.is_relative_to(root) for root in roots):
            continue
        if ppid != "1":
            continue
        try:
            hours = elapsed_hours(elapsed)
        except (TypeError, ValueError):
            continue
        if hours < min_age_hours:
            continue
        found.append({"pid": int(pid), "data": str(data), "hours": round(hours, 2)})
    return found


def sweep_temp(roots, min_age_hours=24.0, apply=False, emit=print):
    clusters = temp_clusters(roots, min_age_hours)
    for cluster in clusters:
        if not apply:
            emit(json.dumps({"action": "preview", "kind": "temp-cluster", "pid": cluster["pid"],
                             "data": cluster["data"], "hours": cluster["hours"]}))
            continue
        current = [c for c in temp_clusters(roots, min_age_hours) if c["pid"] == cluster["pid"]]
        if not current:
            emit(json.dumps({"action": "skip", "kind": "temp-cluster", "pid": cluster["pid"],
                             "reason": "changed"}))
            continue
        os.kill(cluster["pid"], signal.SIGTERM)
        for _ in range(20):
            time.sleep(0.5)
            if subprocess.run(["ps", "-p", str(cluster["pid"])], capture_output=True,
                              check=False).returncode != 0:
                break
        else:
            emit(json.dumps({"action": "skip", "kind": "temp-cluster", "pid": cluster["pid"],
                             "reason": "still-running"}))
            continue
        data = Path(cluster["data"])
        if (not data.is_symlink() and data.exists()
                and any(data != root and data.is_relative_to(root) for root in roots)):
            shutil.rmtree(data)
        emit(json.dumps({"action": "remove", "kind": "temp-cluster", "pid": cluster["pid"],
                         "data": cluster["data"]}))
    return clusters


# --- memory pressure and idle dev servers -------------------------------------

DEV_SERVER = re.compile(
    r"craco/scripts/start\.js|/craco start\b|react-scripts/scripts/start\.js"
    r"|/next/dist/bin/next dev\b|node_modules/\.bin/(?:next|vite|webpack|serve)\b"
    r"|\bwebpack serve\b|\bvite (?:--|dev|serve)\b"
)
EMULATOR = re.compile(r"(?:^|/)emulator .*-avd |qemu-system-\w+ ")
HEAP = re.compile(r"-Xmx(\d+)([kKmMgG])\b")
MEMORY_UNIT = {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}
MEMORY_SIZE = re.compile(r"([\d.]+)([KMG])")


def processes():
    """pid/ppid/elapsed/ RSS table for process-level checks."""
    rows = []
    for line in run(["ps", "-axo", "pid=,ppid=,etime=,rss=,command="]).splitlines():
        fields = line.split(None, 4)
        if len(fields) != 5:
            continue
        pid, ppid, elapsed, rss, command = fields
        try:
            rows.append({"pid": int(pid), "ppid": int(ppid), "etime": elapsed,
                         "rss": int(rss) * 1024, "command": command})
        except ValueError:
            continue
    return rows


def system_value(name):
    try:
        return run(["sysctl", "-n", name]).strip()
    except Refused:
        return ""


def parse_size(text):
    match = MEMORY_SIZE.search(str(text))
    if not match:
        return 0
    return int(float(match.group(1)) * MEMORY_UNIT[match.group(2)])


def swap_usage():
    values = {"total_bytes": 0, "used_bytes": 0, "free_bytes": 0}
    for key, size in re.findall(r"(\w+)\s*=\s*([\d.]+[KMG])", system_value("vm.swapusage")):
        if key.lower() in {"total", "used", "free"}:
            values[key.lower() + "_bytes"] = parse_size(size)
    return values


def vm_stat():
    values, page = {}, 4096
    for line in run(["vm_stat"]).splitlines():
        if "page size of" in line:
            match = re.search(r"page size of (\d+)", line)
            if match:
                page = int(match.group(1))
            continue
        key, _, rest = line.partition(":")
        digits = re.findall(r"\d+", rest)
        if key.strip() and digits:
            values[key.strip()] = int(digits[0]) * page
    return values


def heavy_processes(rows):
    """Processes whose footprint is worth reporting before heavy work."""
    heavy = []
    for row in rows:
        if EMULATOR.search(row["command"]):
            kind = "emulator"
        elif DEV_SERVER.search(row["command"]):
            kind = "dev-server"
        elif HEAP.search(row["command"]):
            kind = "jvm"
        elif "Virtualization.VirtualMachine" in row["command"]:
            kind = "docker-vm"
        else:
            continue
        heavy.append({"pid": row["pid"], "kind": kind, "rss": row["rss"],
                      "command": row["command"][:200]})
    return sorted(heavy, key=lambda item: -item["rss"])


def heap_bytes(command):
    match = HEAP.search(command)
    return int(int(match.group(1)) * MEMORY_UNIT[match.group(2).upper()]) if match else 0


def footprint_table(limit=32):
    """Best-effort per-process footprint: RSS alone hides compressed pages."""
    try:
        text = run(["top", "-l", "2", "-stats", "pid,mem,cmprs,command", "-o", "mem",
                    "-n", str(limit)])
    except (Refused, subprocess.TimeoutExpired):
        return {}
    found = {}
    for line in text.splitlines():
        fields = line.split(None, 3)
        if len(fields) != 4 or not fields[0].isdigit():
            continue
        found[int(fields[0])] = parse_size(fields[1])
    return found


def memory_report(top=10):
    """Read-only memory breakdown; no process is signalled."""
    rows = processes()
    stats = vm_stat()
    footprint = footprint_table(max(top, 24))

    def describe(row):
        return {"pid": row["pid"], "ppid": row["ppid"],
                "hours": round(_hours(row["etime"]), 2), "rss": row["rss"],
                "footprint": footprint.get(row["pid"]),
                "command": row["command"][:200]}

    report = {
        "action": "inspect",
        "kind": "memory",
        "total_bytes": int(system_value("hw.memsize") or 0),
        "swap": swap_usage(),
        "compressor_bytes": stats.get("Pages stored in compressor", 0),
        "compressor_occupied_bytes": stats.get("Pages occupied by compressor", 0),
        "wired_bytes": stats.get("Pages wired down", 0),
        "process_count": len(rows),
        "process_rss_bytes": sum(row["rss"] for row in rows),
        "footprint_available": bool(footprint),
        "top": [describe(row) for row in sorted(rows, key=lambda item: -item["rss"])[:top]],
        "heavy": [{**item, "footprint": footprint.get(item["pid"])}
                  for item in heavy_processes(rows)],
        "idle_servers": stale_servers(0.0, rows),
        "warnings": [],
    }
    for item in report["heavy"]:
        if item["kind"] == "emulator" and (item["footprint"] or 0) >= 4 * MEMORY_UNIT["G"]:
            report["warnings"].append({"reason": "heavy-emulator", "pid": item["pid"],
                                       "footprint_bytes": item["footprint"]})
    if report["swap"]["used_bytes"] and report["swap"]["used_bytes"] * 2 >= report["swap"]["total_bytes"]:
        report["warnings"].append({"reason": "swap-pressure", "used_bytes": report["swap"]["used_bytes"],
                                   "total_bytes": report["swap"]["total_bytes"]})
    if report["total_bytes"] and report["compressor_bytes"] * 5 >= report["total_bytes"]:
        report["warnings"].append({"reason": "compressor-pressure", "bytes": report["compressor_bytes"]})
    for row in rows:
        if heap_bytes(row["command"]) >= 6 * MEMORY_UNIT["G"]:
            report["warnings"].append({"reason": "oversized-jvm-heap", "pid": row["pid"],
                                       "heap_bytes": heap_bytes(row["command"])})
    return report


def _hours(etime):
    try:
        return elapsed_hours(etime)
    except (TypeError, ValueError):
        return 0.0


def server_clients(pid):
    try:
        rows = run(["lsof", "-nP", "-a", "-p", str(pid), "-iTCP", "-sTCP:ESTABLISHED"])
    except Refused:
        return 0
    return len([line for line in rows.splitlines()[1:] if line.strip()])


def stale_servers(min_age_hours=8.0, rows=None):
    """Dev servers older than the gate with no established client."""
    found = []
    for row in processes() if rows is None else rows:
        if not DEV_SERVER.search(row["command"]):
            continue
        hours = _hours(row["etime"])
        if hours < min_age_hours or server_clients(row["pid"]):
            continue
        found.append({"pid": row["pid"], "ppid": row["ppid"], "hours": round(hours, 2),
                      "rss": row["rss"], "command": row["command"][:200]})
    return found


def descendants(rows, pid):
    children = {}
    for row in rows:
        children.setdefault(row["ppid"], []).append(row["pid"])
    found, stack = [], [pid]
    while stack:
        for child in children.get(stack.pop(), []):
            found.append(child)
            stack.append(child)
    return found


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def sweep_servers(min_age_hours=8.0, apply=False, emit=print):
    """Stop only long-idle dev servers (never emulators, never JVMs)."""
    servers = stale_servers(min_age_hours)
    stopped = set()
    for server in servers:
        if server["pid"] in stopped:
            continue
        if not apply:
            emit(json.dumps({"action": "preview", "kind": "dev-server", "pid": server["pid"],
                             "hours": server["hours"], "rss": server["rss"],
                             "command": server["command"]}))
            continue
        rows = processes()
        current = [s for s in stale_servers(min_age_hours, rows) if s["pid"] == server["pid"]]
        if not current:
            emit(json.dumps({"action": "skip", "kind": "dev-server", "pid": server["pid"],
                             "reason": "changed"}))
            continue
        targets = [server["pid"], *descendants(rows, server["pid"])]
        stopped.update(targets)
        for pid in targets:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for _ in range(20):
            if not any(alive(pid) for pid in targets):
                break
            time.sleep(0.5)
        else:
            emit(json.dumps({"action": "skip", "kind": "dev-server", "pid": server["pid"],
                             "reason": "still-running"}))
            continue
        emit(json.dumps({"action": "remove", "kind": "dev-server", "pid": server["pid"],
                         "stopped": targets}))
    return servers


# --- caches: unused Gradle version caches -------------------------------------

SKIP_DIRS = {".git", "node_modules", "vendor", "Library", ".gradle", "DerivedData", ".next", "build"}


def used_gradle_versions(root, depth=6):
    versions = set()
    base = Path(root)
    for current, dirs, files in os.walk(base):
        here = Path(current)
        if len(here.relative_to(base).parts) >= depth:
            dirs[:] = []
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "gradle-wrapper.properties" in files:
            try:
                text = (here / "gradle-wrapper.properties").read_text(errors="replace")
            except OSError:
                continue
            for match in GRADLE_DISTRIBUTION.finditer(text):
                versions.add(match.group(1))
    return versions


def gradle_cache_plan(cache_root, projects_root):
    cache_root = Path(cache_root)
    versions = {p.name: p for p in cache_root.iterdir()
                if p.is_dir() and GRADLE_VERSION.fullmatch(p.name)} if cache_root.is_dir() else {}
    used = used_gradle_versions(projects_root)
    stale = {name: path for name, path in versions.items() if name not in used}
    return used, sorted(stale.items())


def wrapper_dists(wrapper_root, used):
    """Downloaded distributions no scanned wrapper asks for."""
    root = Path(wrapper_root)
    if not root.is_dir():
        return []
    stale = []
    for entry in root.iterdir():
        match = GRADLE_DIST_DIR.fullmatch(entry.name)
        if entry.is_dir() and match and match.group(1) not in used:
            stale.append((entry.name, entry))
    return sorted(stale)


def directory_size(path):
    try:
        blocks = run(["du", "-sk", str(path)]).split()[0]
    except (Refused, IndexError, ValueError):
        return 0
    return int(blocks) * 1024


def sweep_caches(cache_root, projects_root, apply=False, emit=print):
    used, stale = gradle_cache_plan(cache_root, projects_root)
    dist_root = Path(cache_root).parent / "wrapper/dists"
    emit(json.dumps({"action": "inspect", "kind": "gradle", "used": sorted(used),
                     "retained": ["modules-2", "jars-9", "journal-1"]}))
    total = 0
    for name, path in stale:
        size = directory_size(path)
        if not apply:
            emit(json.dumps({"action": "preview", "kind": "gradle-cache", "version": name,
                             "bytes": size}))
            continue
        if Path(path) != Path(cache_root) / name or not GRADLE_VERSION.fullmatch(name):
            raise Refused("Gradle cache path changed; refusing removal")
        if name in used_gradle_versions(projects_root):
            emit(json.dumps({"action": "skip", "kind": "gradle-cache", "version": name,
                             "reason": "now-used"}))
            continue
        shutil.rmtree(path)
        total += size
        emit(json.dumps({"action": "remove", "kind": "gradle-cache", "version": name,
                         "bytes": size}))
    for name, path in wrapper_dists(dist_root, used):
        size = directory_size(path)
        if not apply:
            emit(json.dumps({"action": "preview", "kind": "gradle-dist", "dist": name,
                             "bytes": size}))
            continue
        if Path(path).parent != dist_root or not GRADLE_DIST_DIR.fullmatch(name):
            raise Refused("Gradle distribution path changed; refusing removal")
        if name.split("-")[1] in used_gradle_versions(projects_root):
            emit(json.dumps({"action": "skip", "kind": "gradle-dist", "dist": name,
                             "reason": "now-used"}))
            continue
        shutil.rmtree(path)
        total += size
        emit(json.dumps({"action": "remove", "kind": "gradle-dist", "dist": name,
                         "bytes": size}))
    return stale, total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("labels", "cleanup", "sweep", "caches", "mem"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--repo-dir", type=Path, action="append", default=[])
    parser.add_argument("--projects-root", type=Path, default=Path.home() / "PROJECTS")
    parser.add_argument("--gradle-cache", type=Path, default=Path.home() / ".gradle/caches")
    parser.add_argument("--task")
    parser.add_argument("--context", default="kiri")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--commit")
    parser.add_argument("--min-age-hours", type=float, default=24.0)
    parser.add_argument("--anonymous-volumes", action="store_true")
    parser.add_argument("--temp-clusters", action="store_true")
    parser.add_argument("--idle-servers", action="store_true")
    parser.add_argument("--min-idle-hours", type=float, default=8.0)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.min_age_hours < 0 or not args.min_age_hours < 10 ** 6:
            raise Refused("Invalid age gate")
        if args.min_idle_hours < 0 or not args.min_idle_hours < 10 ** 6:
            raise Refused("Invalid idle gate")
        if args.action in ("labels", "cleanup"):
            if not args.task:
                raise Refused("--task is required")
            expected = labels(args.repo, args.task)
            if args.action == "labels":
                if args.apply:
                    raise Refused("--apply is only valid for cleanup")
                try:
                    remember(args.repo, args.task)
                except OSError as exc:
                    # Recording is a convenience for later sweeps, never a gate.
                    print(f"warning: cannot record repo identity: {exc}", file=sys.stderr)
                print(json.dumps(expected, sort_keys=True))
            else:
                verify_delivery(args.repo, args.commit or "", args.remote)
                cleanup(Docker(args.context), expected, args.apply)
        elif args.action == "sweep":
            sweep(Docker(args.context), args.repo_dir, args.anonymous_volumes, args.apply,
                  args.min_age_hours)
            if args.temp_clusters:
                sweep_temp(temp_roots(), args.min_age_hours, args.apply)
            if args.idle_servers:
                sweep_servers(args.min_idle_hours, args.apply)
        elif args.action == "mem":
            if args.apply:
                raise Refused("--apply is only valid for cleanup, sweep and caches")
            if not 1 <= args.top <= 100:
                raise Refused("Invalid --top")
            print(json.dumps(memory_report(args.top), sort_keys=True))
        else:
            if args.apply and not args.gradle_cache.is_dir():
                raise Refused("Gradle cache directory is missing")
            sweep_caches(args.gradle_cache, args.projects_root, args.apply)
        return 0
    except (Refused, OSError, ValueError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
