#!/usr/bin/env python3
"""Durable, cooperative integration reservations. Never executes Git mutations.

Plane owns tasks. This private local journal owns only resource grants and their
reconciliation. A lease expiry is uncertainty, NOT permission to steal a grant.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import subprocess
import sys
import time
import uuid


class Blocked(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Blocked(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def text(value, name):
    require(isinstance(value, str) and 0 < len(value) <= 512
            and not any(ord(c) < 32 for c in value), f"Invalid {name}")
    return value


def run(argv):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(LC_ALL="C", GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(argv, env=env, text=True, capture_output=True, timeout=10)
    require(result.returncode == 0, result.stderr.strip() or "Command failed")
    return result.stdout.rstrip("\n")


def git(path, *args):
    return run(["git", "-C", str(path), *args])


def identity(path):
    script = Path(__file__).resolve().parents[1] / "pi-skill/workspace-guard/identity.mjs"
    return json.loads(run(["node", str(script), "--root", str(path)]))


def repo_identity(path):
    fields = git(path, "worktree", "list", "--porcelain", "-z").split("\0")
    require(fields[0].startswith("worktree ") and "bare" not in fields,
            "Non-bare repository required")
    primary = str(Path(fields[0][9:]).resolve(strict=True))
    common = str(Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir"))
                 .resolve(strict=True))
    return primary, common


def commit(path, ref):
    text(ref, "revision")
    return git(path, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}")


def plan(args):
    project = identity(args.root)
    repos = []
    for path, revision in args.repo:
        path = Path(path)
        if not path.is_absolute():
            path = Path(args.root) / path
        primary, common = repo_identity(path)
        require(identity(primary)["projectId"] == project["projectId"],
                "Repository must belong to the same existing Paseo project")
        checkout_branch = git(primary, "symbolic-ref", "--quiet", "HEAD")
        branch = checkout_branch
        if args.target_branch:
            git(primary, "check-ref-format", "--branch", args.target_branch)
            branch = "refs/heads/" + args.target_branch
        repos.append({"path": primary, "common_dir": common, "branch": branch,
                      "checkout_branch": checkout_branch, "checkout_head": commit(primary, "HEAD"),
                      "expected_head": commit(primary, branch),
                      "candidate_head": commit(primary, revision)})
    request = {"schema": 1, "id": args.id, "project_id": project["projectId"],
               "root": project["root"],
               "plane": {"project_id": args.plane_project, "work_item_id": args.plane_item},
               "repositories": repos, "resources": args.resource, "depends_on": args.after}
    return validate_request(request)


def validate_request(request):
    require(isinstance(request, dict) and set(request) == {
        "schema", "id", "project_id", "root", "plane", "repositories", "resources", "depends_on"
    } and request["schema"] == 1, "Malformed queue request schema")
    for key in ("id", "project_id", "root"):
        text(request[key], key)
    require(isinstance(request["plane"], dict)
            and set(request["plane"]) == {"project_id", "work_item_id"}, "Plane identity required")
    for value in request["plane"].values():
        require(isinstance(value, str) and str(uuid.UUID(value)) == value, "Invalid Plane UUID")
    require(isinstance(request["repositories"], list) and 0 < len(request["repositories"]) <= 32,
            "Select 1–32 affected repositories")
    require(isinstance(request["resources"], list) and len(request["resources"]) <= 64,
            "Invalid extra resources")
    for resource in request["resources"]:
        text(resource, "resource")
        require(resource.startswith("external:") and len(resource) > 9,
                "Extra shared resources must use external:namespace:name")
    require(isinstance(request["depends_on"], list) and len(request["depends_on"]) <= 64,
            "Invalid dependencies")
    for dependency in request["depends_on"]:
        text(dependency, "dependency")
        require(dependency != request["id"], "Self dependency is forbidden")
    require(len(set(request["depends_on"])) == len(request["depends_on"]), "Duplicate dependency")
    seen = set()
    for repo in request["repositories"]:
        require(isinstance(repo, dict) and set(repo) == {
            "path", "common_dir", "branch", "checkout_branch", "checkout_head",
            "expected_head", "candidate_head"
        }, "Invalid repository vector")
        for value in repo.values():
            text(value, "repository field")
        require(Path(repo["path"]).is_absolute() and Path(repo["common_dir"]).is_absolute(),
                "Repository paths must be canonical absolute paths")
        require(repo["common_dir"] not in seen, "Duplicate repository/common directory")
        seen.add(repo["common_dir"])
        require(all(repo[key].startswith("refs/heads/") for key in ("branch", "checkout_branch")),
                "Target and checkout must be branches")
        for key in ("expected_head", "candidate_head", "checkout_head"):
            require(len(repo[key]) in (40, 64) and all(c in "0123456789abcdef" for c in repo[key]),
                    "Commit vector must contain full pinned hashes")
    request = json.loads(encoded(request))
    request["repositories"].sort(key=lambda repo: repo["common_dir"])
    request["resources"] = sorted(set(request["resources"]))
    request["depends_on"].sort()
    return request


def resources(request):
    return set(request["resources"]) | {"repo:" + r["common_dir"] for r in request["repositories"]}


def observe(request):
    project = identity(request["root"])
    require(project["projectId"] == request["project_id"] and project["root"] == request["root"],
            "Paseo project identity changed")
    result = []
    for repo in request["repositories"]:
        path = repo["path"]
        primary, common = repo_identity(path)
        require((primary, common) == (path, repo["common_dir"]), "Repository identity changed")
        require(identity(path)["projectId"] == request["project_id"], "Repository project changed")
        require(git(path, "symbolic-ref", "--quiet", "HEAD") == repo["checkout_branch"],
                "Target checkout branch changed")
        # Ref-only integration must never change a branch checked out elsewhere.
        fields = git(path, "worktree", "list", "--porcelain", "-z").split("\0")
        location = None
        for field in fields:
            if field.startswith("worktree "):
                location = str(Path(field[9:]).resolve())
            elif field == "branch " + repo["branch"]:
                require(location == path and repo["branch"] == repo["checkout_branch"],
                        "Target branch is checked out in another worktree")
        if repo["branch"] != repo["checkout_branch"]:
            require(commit(path, "HEAD") == repo["checkout_head"],
                    "Unrelated primary checkout HEAD changed; preserve and reconcile")
        git_dir = Path(git(path, "rev-parse", "--absolute-git-dir"))
        require(not any((git_dir / marker).exists() for marker in (
            "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply",
            "sequencer", "index.lock"
        )), "Unresolved Git operation; preserve and reconcile")
        require(not git(path, "status", "--porcelain=v1", "--untracked-files=all"),
                "Target checkout is dirty; preserve and reconcile")
        # Resolve both objects again; pruned/replaced objects must never be silently accepted.
        require(commit(path, repo["expected_head"]) == repo["expected_head"]
                and commit(path, repo["candidate_head"]) == repo["candidate_head"],
                "Commit objects changed")
        result.append(commit(path, repo["branch"]))
    return result


def vector_matches(request, key):
    actual = observe(request)
    require(actual == [repo[key] for repo in request["repositories"]],
            f"Commit vector differs from {key}; refresh/review or reconcile partial delivery")


def load_json(path):
    require(Path(path).stat().st_size <= 1024 * 1024, "JSON exceeds 1 MiB")
    return json.loads(Path(path).read_text())


def evidence(path):
    file = Path(path)
    require(file.is_file() and not file.is_symlink(), "Reconciliation needs a regular evidence file")
    data = file.read_bytes()
    require(0 < len(data) <= 1024 * 1024, "Reconciliation evidence must be nonempty, <=1 MiB")
    return {"path": str(file.resolve()), "sha256": hashlib.sha256(data).hexdigest()}


class Queue:
    def __init__(self, home):
        self.home = Path(home).expanduser().absolute()
        self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.home.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
                and not info.st_mode & 0o077, "Queue directory must be owned, private (0700), non-symlink")
        database = self.home / "queue.sqlite3"
        require(not database.is_symlink(), "Queue database cannot be a symlink")
        if database.exists():
            info = database.stat()
            require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and not info.st_mode & 0o077, "Queue database must be an owned private regular file")
        # Create with private permissions atomically, including simultaneous first use.
        try:
            fd = os.open(database, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        self.db = sqlite3.connect(database, timeout=5, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            require(version in (0, 1), "Unsupported queue database version")
            self.db.execute("""CREATE TABLE IF NOT EXISTS requests (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                request TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued',
                owner TEXT, token TEXT, expires REAL, reason TEXT NOT NULL DEFAULT '',
                recovery TEXT, updated REAL NOT NULL)""")
            self.db.execute("PRAGMA user_version=1")
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def rows(self):
        return [dict(row) | {"request": json.loads(row["request"])}
                for row in self.db.execute("SELECT * FROM requests ORDER BY seq")]

    def row(self, request_id):
        rows = [r for r in self.rows() if r["id"] == request_id]
        require(len(rows) == 1, "Unknown queue request")
        return rows[0]

    def dependency_reason(self, row, rows):
        by_id = {r["id"]: r for r in rows}
        for dep in row["request"]["depends_on"]:
            other = by_id[dep]
            if other["state"] != "completed":
                return f"dependency:{dep}:{other['state']}"
        return ""

    def wait_reason(self, row, rows):
        if row["state"] != "queued":
            return row["reason"] or row["state"]
        dependency = self.dependency_reason(row, rows)
        if dependency:
            return dependency
        wanted = resources(row["request"])
        for other in rows:
            if other["id"] == row["id"] or not wanted.intersection(resources(other["request"])):
                continue
            if other["state"] in ("active", "held"):
                stale = other["state"] == "held" or other["expires"] <= time.time()
                return f"{'reconcile' if stale else 'resource'}:{other['id']}"
            if (other["state"] == "queued" and other["seq"] < row["seq"]
                    and not self.dependency_reason(other, rows)):
                return f"fifo:{other['id']}"
        return ""

    def public(self, row, rows=None):
        result = {k: v for k, v in row.items() if k != "token"}
        result["wait_reason"] = self.wait_reason(row, rows or self.rows())
        result["needs_reconcile"] = row["state"] == "held" or (
            row["state"] == "active" and row["expires"] <= time.time())
        return result

    def mutate(self, args):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = self._mutate(args)
            self.db.commit()
            return result
        except BaseException:
            self.db.rollback()
            raise

    def _mutate(self, args):
        action = args.action
        now = time.time()
        if action in ("enqueue", "refresh"):
            request = validate_request(load_json(args.request))
            existing = [r for r in self.rows() if r["id"] == request["id"]]
            if action == "enqueue" and existing:
                require(existing[0]["request"] == request, "Idempotency key reused with different request")
                return self.public(existing[0])
            vector_matches(request, "expected_head")
            rows = self.rows()
            require(all(any(r["id"] == dep for r in rows) for dep in request["depends_on"]),
                    "Dependencies must already exist; forward/cyclic dependencies are forbidden")
            if action == "refresh":
                old = self.row(request["id"])
                require(old["state"] == "queued", "Only queued requests can refresh")
                previous = old["request"]
                def targets(value):
                    return [tuple(repo[key] for key in ("path", "common_dir", "branch", "checkout_branch"))
                            for repo in value["repositories"]]
                require(all(request[key] == previous[key] for key in (
                    "plane", "project_id", "root", "resources", "depends_on"))
                    and resources(request) == resources(previous)
                    and targets(request) == targets(previous),
                    "Refresh must preserve target identity, resources and dependencies")
                proof = evidence(args.evidence)
                self.db.execute("UPDATE requests SET request=?, reason='', recovery=?, updated=? WHERE id=?",
                                (encoded(request), encoded(proof), now, request["id"]))
            else:
                self.db.execute("INSERT INTO requests(id,request,updated) VALUES (?,?,?)",
                                (request["id"], encoded(request), now))
            return self.public(self.row(request["id"]))
        row = self.row(args.id)
        if action == "cancel":
            if row["state"] == "cancelled":
                return self.public(row)
            require(row["state"] == "queued", "Only queued work can be cancelled; active work needs reconciliation")
            self.db.execute("UPDATE requests SET state='cancelled',reason=?,updated=? WHERE id=?",
                            (text(args.reason, "reason"), now, args.id))
        elif action == "claim":
            text(args.owner, "owner")
            if row["state"] == "active" and row["owner"] == args.owner and row["expires"] > now:
                return self.public(row) | {"token": row["token"]}
            reason = self.wait_reason(row, self.rows())
            if reason:
                return self.public(row)
            vector_matches(row["request"], "expected_head")
            self.db.execute("UPDATE requests SET state='active',owner=?,token=?,expires=?,updated=? WHERE id=?",
                            (args.owner, secrets.token_hex(24), now + args.lease_seconds, now, args.id))
            row = self.row(args.id)
            return self.public(row) | {"token": row["token"]}
        elif action == "reconcile":
            require(args.owner_stopped, "Explicit old-writer-stopped attestation required")
            require(row["state"] in ("active", "held"), "Only held/active grants need reconciliation")
            proof = evidence(args.evidence)
            if args.outcome == "resume":
                actual = observe(row["request"])
                require(all(head in (repo["expected_head"], repo["candidate_head"])
                            for head, repo in zip(actual, row["request"]["repositories"])),
                        "Unknown target vector; preserve all reservations and reconcile manually")
                text(args.owner, "replacement owner")
                self.db.execute("""UPDATE requests SET state='active',owner=?,token=?,expires=?,
                    reason='',recovery=?,updated=? WHERE id=?""",
                                (args.owner, secrets.token_hex(24), time.time() + args.lease_seconds,
                                 encoded(proof), now, args.id))
                fresh = self.row(args.id)
                remaining = [repo["path"] for head, repo in zip(actual, row["request"]["repositories"])
                             if head != repo["candidate_head"]]
                return self.public(fresh) | {"token": fresh["token"], "remaining_repositories": remaining}
            key = "candidate_head" if args.outcome == "completed" else "expected_head"
            vector_matches(row["request"], key)
            state = "queued" if args.outcome == "retry" else args.outcome
            self.db.execute("""UPDATE requests SET state=?,token=NULL,owner=NULL,expires=NULL,
                reason='',recovery=?,updated=? WHERE id=?""", (state, encoded(proof), now, args.id))
        else:
            require(row["state"] == "active" and row["token"] == args.token
                    and row["owner"] == args.owner and row["expires"] > now,
                    "Grant absent, expired or owner/token mismatch; reconcile without replay")
            if action == "heartbeat":
                self.db.execute("UPDATE requests SET expires=?,updated=? WHERE id=?",
                                (now + args.lease_seconds, now, args.id))
            elif action == "hold":
                self.db.execute("UPDATE requests SET state='held',reason=?,updated=? WHERE id=?",
                                (text(args.reason, "reason"), now, args.id))
            elif action == "finish":
                vector_matches(row["request"], "candidate_head" if args.outcome == "completed" else "expected_head")
                self.db.execute("UPDATE requests SET state=?,token=NULL,expires=NULL,updated=? WHERE id=?",
                                (args.outcome, now, args.id))
            else:
                raise Blocked("Unknown action")
        return self.public(self.row(args.id))


def bounded_int(low, high):
    def parse(value):
        number = int(value)
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f"Expected {low}–{high}")
        return number
    return parse


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--home", default=os.environ.get("MEGAI_QUEUE_HOME", str(Path.home() / ".megai/queue")),
                        help="One shared private queue directory per machine; never per-worktree")
    actions = result.add_subparsers(dest="action", required=True)
    p = actions.add_parser("plan", help="Read-only pinned repo vector for an existing Paseo project")
    for name in ("root", "id", "plane-project", "plane-item"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--repo", nargs=2, action="append", required=True, metavar=("PATH", "CANDIDATE"))
    p.add_argument("--target-branch", help="Explicit target ref in every repo; default is each primary's current branch")
    p.add_argument("--resource", action="append", default=[])
    p.add_argument("--after", action="append", default=[])
    for name in ("enqueue", "refresh"):
        p = actions.add_parser(name)
        p.add_argument("--request", required=True)
        if name == "refresh":
            p.add_argument("--evidence", required=True)
    p = actions.add_parser("status")
    p.add_argument("--id")
    for name in ("claim", "heartbeat", "hold", "finish", "cancel", "reconcile"):
        p = actions.add_parser(name)
        p.add_argument("--id", required=True)
        if name in ("claim", "heartbeat", "hold", "finish"):
            p.add_argument("--owner", required=True)
        if name in ("heartbeat", "hold", "finish"):
            p.add_argument("--token", required=True)
        if name in ("claim", "heartbeat"):
            p.add_argument("--lease-seconds", type=bounded_int(1, 300), default=120)
        if name == "claim":
            p.add_argument("--wait-seconds", type=bounded_int(0, 240), default=0)
        if name in ("hold", "cancel"):
            p.add_argument("--reason", required=True)
        if name in ("finish", "reconcile"):
            outcomes = ["completed", "failed"] + (["retry", "resume"] if name == "reconcile" else [])
            p.add_argument("--outcome", choices=outcomes, required=True)
        if name == "reconcile":
            p.add_argument("--owner-stopped", action="store_true")
            p.add_argument("--evidence", required=True)
            p.add_argument("--owner", help="New unique executor identity for resume")
            p.add_argument("--lease-seconds", type=bounded_int(1, 300), default=120)
    return result


def main():
    args = parser().parse_args()
    try:
        if args.action == "plan":
            print(encoded(plan(args)))
            return 0
        queue = Queue(args.home)
        try:
            if args.action == "status":
                rows = queue.rows()
                value = queue.public(queue.row(args.id), rows) if args.id else [queue.public(r, rows) for r in rows]
            else:
                deadline = time.monotonic() + getattr(args, "wait_seconds", 0)
                while True:
                    value = queue.mutate(args)
                    if (args.action != "claim" or "token" in value
                            or value["state"] != "queued" or time.monotonic() >= deadline):
                        break
                    time.sleep(min(0.25, max(0, deadline - time.monotonic())))
            print(encoded(value))
            return 2 if args.action == "claim" and "token" not in value else 0
        finally:
            queue.db.close()
    except (Blocked, OSError, ValueError, sqlite3.Error, subprocess.SubprocessError) as error:
        print(encoded({"status": "BLOCKED", "reason": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
