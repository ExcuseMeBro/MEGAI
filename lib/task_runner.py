#!/usr/bin/env python3
"""Explicit, dependency-free task worktrees and source-pinned dev delivery.

No launch hook, daemon, Plane client or automatic reconciliation.
Finish includes cleanup only when the caller verifies task resources are released.
The caller must verify the existing Plane task/authority before start or delivery.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import integration_queue as queue


require = queue.require
Blocked = queue.Blocked


def git(path, *args):
    return queue.git(path, *args)


def head(path, ref="HEAD"):
    return queue.commit(path, ref)


def save(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("x", encoding="utf8") as stream:
        os.chmod(temp, 0o600)
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    os.replace(temp, path)


def clean(path):
    directory = Path(git(path, "rev-parse", "--absolute-git-dir"))
    require(not any((directory / name).exists() for name in (
        "MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge",
        "rebase-apply", "sequencer", "index.lock", "HEAD.lock")), "Git operation is busy")
    require(not git(path, "status", "--porcelain=v1", "--untracked-files=all"),
            "Checkout is dirty; preserve files and reconcile")


def remote(path):
    fetch = git(path, "remote", "get-url", "--all", "origin").splitlines()
    push = git(path, "remote", "get-url", "--push", "--all", "origin").splitlines()
    require(len(fetch) == 1 and fetch == push, "origin fetch/push URLs must match exactly")
    return fetch[0]


def fetch_dev(path):
    git(path, "fetch", "--no-tags", "origin", "+refs/heads/dev:refs/remotes/origin/dev")
    observed = git(path, "ls-remote", "--exit-code", "origin", "refs/heads/dev").split()
    require(len(observed) == 2 and observed[1] == "refs/heads/dev"
            and observed[0] == head(path, queue.REMOTE_DEV_REF), "Remote dev moved during observation")
    return observed[0]


def uuid_arg(value):
    try:
        require(str(uuid.UUID(value)) == value, "Use canonical Plane UUIDs")
        return value
    except (ValueError, Blocked) as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def metadata(root, task):
    primary, common = queue.repo_identity(root)
    directory = Path(common) / "megai-tasks" / task
    return primary, common, directory


@contextmanager
def task_lock(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "writer.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Blocked("Another task helper is active") from error
        yield


def load_task(args):
    primary, common, directory = metadata(args.root, args.task)
    data = queue.load_json(directory / "owner.json")
    require(data["primary"] == primary and data["common"] == common
            and data["task"] == args.task, "Task ownership changed")
    require(queue.repo_identity(data["worktree"]) == (primary, common), "Worktree identity changed")
    require(git(data["worktree"], "symbolic-ref", "--quiet", "HEAD") == data["branch"],
            "Task branch changed")
    require(remote(primary) == data["remote"], "origin URL changed")
    require(queue.identity(primary) == data["identity"], "Project identity changed")
    return data, directory


def preflight(data, base=None):
    primary, worktree = data["primary"], data["worktree"]
    clean(worktree)
    clean(primary)
    require(queue.repo_identity(worktree) == (primary, data["common"])
            and git(worktree, "symbolic-ref", "--quiet", "HEAD") == data["branch"]
            and queue.identity(primary) == data["identity"], "Project/task ownership changed")
    require(git(primary, "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev",
            "Primary checkout must be on dev")
    require(remote(primary) == data["remote"], "origin URL changed")
    candidate = head(worktree)
    local = head(primary, "refs/heads/dev")
    upstream = head(primary, queue.REMOTE_DEV_REF)
    require(local == upstream, "Local and fetched remote dev differ; explicit reconciliation required")
    if base:
        require(local == base, "dev advanced; rerun checks and review against current dev")
    require(queue.ancestor(primary, local, candidate), "Candidate diverged from dev; explicit reconciliation required")
    require(candidate != local, "No task commits to deliver")
    return {"candidate": candidate, "base": local}


def start(args):
    primary, common, directory = metadata(args.root, args.task)
    with task_lock(directory):
        require(not (directory / "owner.json").exists(), "Task already owns a worktree; reuse it")
        require(not (directory / "intent.json").exists(), "Prior start intent exists; inspect before retrying")
        require(args.plane_current, "Verify existing Plane project/task and authority first (--plane-current)")
        require(git(primary, "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev", "Primary must be on dev")
        url = remote(primary)
        upstream = fetch_dev(primary)
        require(head(primary, "dev") == upstream, "Local and remote dev differ")
        project = queue.identity(primary)
        selected_path = Path(args.worktree).expanduser()
        require(not selected_path.is_symlink(), "Worktree destination cannot be a symlink")
        path = selected_path.resolve()
        require(not path.exists(), "Worktree destination already exists")
        existing = [Path(field[9:]).resolve() for field in
                    git(primary, "worktree", "list", "--porcelain", "-z").split("\0")
                    if field.startswith("worktree ")]
        require(not any(path.is_relative_to(checkout) for checkout in existing),
                "Worktree must be outside all existing repository checkouts")
        branch = "task/" + args.task
        require(not git(primary, "branch", "--list", branch), "Task branch already exists")
        data = {"schema": 1, "task": args.task, "plane_project": args.project,
                "primary": primary, "common": common, "identity": project,
                "worktree": str(path), "branch": "refs/heads/" + branch,
                "remote": url, "start_base": upstream, "created": time.time()}
        # Intent survives an uncertain worktree-add; never retry an unknown writer.
        save(directory / "intent.json", data)
        git(primary, "worktree", "add", "-b", branch, str(path), upstream)
        save(directory / "owner.json", data)
        return data


def run_check(command, worktree, timeout):
    # Own a process group so timed-out/interrupted checks cannot leave child writers.
    process = subprocess.Popen(command, shell=True, cwd=worktree,
                               env=queue.environment(), start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def verify(args):
    _, _, directory = metadata(args.root, args.task)
    with task_lock(directory):
        data, directory = load_task(args)
        # Verification is private, not a shared delivery reservation. A dirty primary
        # blocks delivery but must not stop independent task testing.
        clean(data["worktree"])
        upstream = fetch_dev(data["primary"])
        require(head(data["primary"], "dev") == upstream, "Local and remote dev differ")
        require(queue.ancestor(data["worktree"], upstream, head(data["worktree"])),
                "Candidate diverged from dev; explicit reconciliation required")
        candidate = head(data["worktree"])
        require(candidate != upstream, "Commit task changes before verification")
        receipt = {"schema": 1, "candidate": candidate, "base": upstream,
                   "task": args.task, "plane_project": data["plane_project"],
                   "checks": [], "passed": False, "time": time.time()}
        save(directory / "verification.json", receipt)  # invalidate previous success first
        for command in args.check:
            started = time.monotonic()
            exit_code = run_check(command, data["worktree"], args.timeout)
            receipt["checks"].append({"command": command, "exit": exit_code,
                                      "seconds": round(time.monotonic() - started, 3)})
            save(directory / "verification.json", receipt)
            require(exit_code == 0, "Check failed; no delivery receipt")
        clean(data["worktree"])
        require(head(data["worktree"]) == candidate
                and head(data["primary"], "dev") == upstream
                and head(data["primary"], queue.REMOTE_DEV_REF) == upstream,
                "Source or dev changed while checks ran")
        receipt["passed"] = True
        save(directory / "verification.json", receipt)
        return receipt


def readiness(args):
    data, directory = load_task(args)
    pins = preflight(data)
    receipt = queue.load_json(directory / "verification.json")
    require(receipt["task"] == data["task"] and receipt["plane_project"] == data["plane_project"]
            and receipt["passed"] and receipt["candidate"] == pins["candidate"]
            and receipt["base"] == pins["base"] and receipt["checks"]
            and all(check["exit"] == 0 for check in receipt["checks"]), "Missing or stale verification")
    return data, directory, pins, receipt


def queue_action(*words, allow_wait=False):
    result = subprocess.run([sys.executable, "-B", str(Path(queue.__file__)), *words],
                            capture_output=True, text=True, env=queue.environment(), timeout=60)
    value = json.loads(result.stdout) if result.stdout.strip() else {}
    waiting = allow_wait and result.returncode == 2 and value.get("state") == "queued"
    require(result.returncode == 0 or waiting,
            result.stdout.strip() or result.stderr.strip() or "Queue action failed")
    return value


def cleanup_owned(data, released):
    """Retain on uncertainty. Never stop sessions or force worktree/ref deletion."""
    retained = {"state": "retained", "worktree": data["worktree"], "branch": data["branch"]}
    if not released:
        return retained | {"reason": "Task resources active or release not verified"}
    try:
        task_path = Path(data["worktree"]).resolve()
        require(not Path.cwd().resolve().is_relative_to(task_path),
                "Current process is inside task worktree")
        require(not any(Path(tool).resolve().is_relative_to(task_path)
                        for tool in (__file__, queue.__file__)),
                "Running lifecycle tools reside in task worktree; retain until released")
        require(Path(data["worktree"]).resolve() == Path(data["worktree"])
                and queue.repo_identity(data["worktree"]) == (data["primary"], data["common"])
                and git(data["worktree"], "symbolic-ref", "--quiet", "HEAD") == data["branch"],
                "Task ownership changed before cleanup")
        clean(data["worktree"])
        clean(data["primary"])
        require(not git(data["worktree"], "clean", "-ndx"),
                "Ignored/untracked data or directories retained")
        candidate = head(data["worktree"])
        require(candidate == data["delivered_candidate"]
                and head(data["primary"], data["branch"]) == candidate
                and git(data["primary"], "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev"
                and remote(data["primary"]) == data["remote"]
                and queue.ancestor(data["primary"], candidate, "refs/heads/dev")
                and queue.ancestor(data["primary"], candidate, queue.REMOTE_DEV_REF),
                "Delivery/ownership changed before cleanup")
        git(data["primary"], "worktree", "remove", data["worktree"])
        # Revalidate immediately before the next shared write. Native safe deletion
        # also refuses a ref that is checked out or not merged.
        clean(data["primary"])
        require(head(data["primary"], data["branch"]) == candidate
                and git(data["primary"], "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev"
                and queue.ancestor(data["primary"], candidate, "refs/heads/dev"),
                "Task/target ref changed after worktree removal; retain branch")
        git(data["primary"], "branch", "-d", data["branch"].removeprefix("refs/heads/"))
        return retained | {"state": "removed", "reason": "Released, clean and verified in local/remote dev"}
    except (Blocked, OSError, subprocess.SubprocessError) as error:
        return retained | {"reason": str(error), "worktree_exists": Path(data["worktree"]).exists()}


def deliver(args):
    require(args.plane_current, "Revalidate Plane task and authority first (--plane-current)")
    require(args.targets_idle, "Verify primary/task checkouts have no other writer (--targets-idle)")
    _, _, directory = metadata(args.root, args.task)
    with task_lock(directory):
        data, _ = load_task(args)
        require(data["identity"]["root"] == data["primary"],
                "Multi-repository projects need one coordinated all-repository delivery; use existing queue")
        queue_home = Path(os.environ.get("MEGAI_QUEUE_HOME", str(Path.home() / ".megai/queue"))).expanduser().resolve()
        checkouts = [Path(field[9:]).resolve() for field in
                     git(data["primary"], "worktree", "list", "--porcelain", "-z").split("\0")
                     if field.startswith("worktree ")]
        require(not any(queue_home.is_relative_to(path) for path in checkouts),
                "Queue home must be shared outside all repository worktrees")
        fetch_dev(data["primary"])
        data, directory, pins, receipt = readiness(args)
        require(args.reviewed_sha == pins["candidate"], "Review must name the exact verified SHA")
        previous = directory / "delivery.json"
        if previous.exists():
            journal = queue.load_json(previous)
            require(journal["state"] == "waiting",
                    "Delivery already attempted; inspect evidence/queue and reconcile, never blindly replay")
            require(all(journal[key] == value for key, value in pins.items())
                    and journal["remote"] == data["remote"]
                    and journal["queue_home"] == str(queue_home),
                    "Waiting delivery pins changed; reconcile queued request before retry")
            request_id = journal["request"]
            waiting = queue_action("status", "--id", request_id)
            require(waiting["state"] == "queued"
                    and waiting["request"] == queue.load_json(directory / "request.json"),
                    "Waiting request changed or may own a grant; inspect before replay")
        else:
            request_id = "task-" + args.task + "-" + uuid.uuid4().hex
            resource = "external:remote-dev:" + hashlib.sha256(data["remote"].encode()).hexdigest()
            request = queue.plan(argparse.Namespace(
                root=data["primary"], id=request_id, plane_project=data["plane_project"],
                plane_item=args.task, repo=[(data["primary"], pins["candidate"])],
                remote_dev=False, target_branch="dev", resource=[resource], after=[]))
            save(directory / "request.json", request)
            journal = {"task": args.task, **pins, "request": request_id,
                       "remote": data["remote"], "queue_home": str(queue_home),
                       "state": "enqueue-intent", "time": time.time()}
            save(previous, journal)
            queue_action("enqueue", "--request", str(directory / "request.json"))
        owner = "task-runner-" + uuid.uuid4().hex
        # An interrupted/uncertain claim is not ordinary waiting and cannot replay.
        journal["state"] = "claim-intent"
        save(previous, journal)
        grant = queue_action("claim", "--id", request_id, "--owner", owner,
                             "--lease-seconds", "300", allow_wait=True)
        if grant.get("state") == "queued" and "token" not in grant:
            journal.update(state="waiting", wait_reason=grant["wait_reason"])
            save(previous, journal)
            raise Blocked("Delivery waiting: " + grant["wait_reason"]
                          + "; same request retained; retry finish/deliver after blocker resolves")
        token = grant["token"]
        journal["state"] = "granted"
        save(directory / "delivery.json", journal)
        def lease():
            queue_action("heartbeat", "--id", request_id, "--owner", owner,
                         "--token", token, "--lease-seconds", "300")
        try:
            require(preflight(data, pins["base"]) == pins, "Candidate changed after review")
            require(fetch_dev(data["primary"]) == pins["base"], "Remote dev advanced; retest")
            require(preflight(data, pins["base"]) == pins, "Candidate changed after review")
            lease()
            require(preflight(data, pins["base"]) == pins, "Candidate changed after review")
            git(data["primary"], "merge", "--ff-only", "--no-overwrite-ignore", pins["candidate"])
            journal["state"] = "local-integrated"
            save(directory / "delivery.json", journal)
            clean(data["primary"])
            clean(data["worktree"])
            require(git(data["primary"], "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev"
                    and head(data["primary"]) == pins["candidate"]
                    and head(data["worktree"]) == pins["candidate"], "Source/target changed before push")
            require(remote(data["primary"]) == data["remote"], "origin URL changed")
            require(fetch_dev(data["primary"]) == pins["base"], "Remote dev advanced before push")
            lease()
            clean(data["primary"])
            clean(data["worktree"])
            require(git(data["primary"], "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev"
                    and head(data["primary"], "dev") == pins["candidate"]
                    and head(data["worktree"]) == pins["candidate"]
                    and head(data["primary"], queue.REMOTE_DEV_REF) == pins["base"]
                    and remote(data["primary"]) == data["remote"], "Delivery vector changed before push")
            git(data["primary"], "push", "origin", pins["candidate"] + ":refs/heads/dev")
            journal["state"] = "pushed-unverified"
            save(directory / "delivery.json", journal)
            require(remote(data["primary"]) == data["remote"], "origin URL changed after push")
            observed = fetch_dev(data["primary"])
            clean(data["primary"])
            require(git(data["primary"], "symbolic-ref", "--quiet", "HEAD") == "refs/heads/dev",
                    "Primary branch changed after push")
            require(queue.ancestor(data["primary"], pins["candidate"], "refs/heads/dev")
                    and queue.ancestor(data["primary"], pins["candidate"], queue.REMOTE_DEV_REF),
                    "Delivered SHA missing from local or remote dev")
            journal.update(state="delivery-verified", observed_remote=observed,
                           local_dev=head(data["primary"], "dev"), verified_at=time.time(),
                           verification=receipt)
            save(directory / "delivery.json", journal)
            lease()
            if args.action == "finish":
                journal["cleanup"] = cleanup_owned(
                    data | {"delivered_candidate": pins["candidate"]}, args.cleanup_released)
                save(directory / "delivery.json", journal)
            lease()
            queue_action("finish", "--id", request_id, "--owner", owner,
                         "--token", token, "--outcome", "completed")
            journal["state"] = "verified"
            save(directory / "delivery.json", journal)
            return journal
        except BaseException:
            # Unknown writes retain all resources. Expired grants are already blocking;
            # hold can fail then, but must never hide the original failure.
            try:
                queue_action("hold", "--id", request_id, "--owner", owner, "--token", token,
                             "--reason", "Task delivery interrupted or failed; inspect journal before reconciliation")
            except (Blocked, subprocess.SubprocessError, OSError):
                pass
            raise


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    actions = result.add_subparsers(dest="action", required=True)
    for name in ("start", "verify", "ready", "deliver", "finish"):
        p = actions.add_parser(name)
        p.add_argument("--root", default=".")
        p.add_argument("--task", type=uuid_arg, required=True, help="Verified existing Plane task UUID")
        if name in ("start", "deliver", "finish"):
            p.add_argument("--plane-current", action="store_true", help="Caller attests live Plane identity/authority checked")
        if name == "start":
            p.add_argument("--project", type=uuid_arg, required=True, help="Verified Plane project UUID")
            p.add_argument("--worktree", required=True)
        if name == "verify":
            p.add_argument("--check", action="append", required=True, help="Explicit shell command; repeat for focused checks")
            p.add_argument("--timeout", type=int, default=600)
        if name in ("deliver", "finish"):
            p.add_argument("--reviewed-sha", required=True, help="Caller attests complete self-review of exact candidate/range")
            p.add_argument("--targets-idle", action="store_true", help="Caller attests primary/task checkouts have no other writer")
        if name == "finish":
            p.add_argument("--cleanup-released", action="store_true",
                           help="Caller freshly verified task resources released (not active/uncertain); never stop sessions")
    return result


def main():
    args = parser().parse_args()
    try:
        if args.action == "ready":
            _, _, pins, receipt = readiness(args)
            value = {"status": "READY_LOCAL", **pins, "checks": receipt["checks"],
                     "note": "No network/queue/Plane check; delivery revalidates all refs"}
        else:
            value = {"start": start, "verify": verify, "deliver": deliver, "finish": deliver}[args.action](args)
        print(json.dumps(value, indent=2))
        return 0
    except (Blocked, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
