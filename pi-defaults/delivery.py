#!/usr/bin/env python3
"""Sweep every task branch into dev and prove it, without stopping on recoverable blockers.

The module exists because `/mdev` used to be prose only: a fresh session had to
re-derive ownership for every branch and halted on the first dirty worktree, moved
ref or Plane timeout. Here the mechanical part is code:

    scan    read-only ledger of task branches, checkouts and writer activity
    run     adopt abandoned work, merge into dev, verify, push, hand off, retire
    resume  replay Plane hand-offs that were journaled while Plane was unreachable
    pr      reuse or open the one dev -> main pull request

Every step is fail-soft per row: one blocked row never aborts the sweep, and
nothing is destroyed -- adoption commits work, retirement backs up ignored data,
and a failed post-merge check rolls dev back to the pre-merge tree.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

TASK_PREFIXES = ("task/",)
PROTECTED = frozenset({"main", "master", "dev", "develop", "production", "prod"})
GIT_OPERATIONS = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "BISECT_LOG")
ACTIVE_MINUTES = 15
MAX_SCAN_FILES = 4000
MAX_BACKUP_BYTES = 64 * 1024 * 1024
MAX_SINGLE_BACKUP = 8 * 1024 * 1024
MAX_LOG = 4000


class Blocked(ValueError):
    """A row that cannot proceed now; the sweep reports it and continues."""


def git(path, *args, check=True, timeout=180):
    result = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, timeout=timeout
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise Blocked(f"git {args[0]} failed in {path}: {detail[-1] if detail else 'unknown error'}")
    return result.stdout.strip() if check else result


def git_ok(path, *args):
    return git(path, *args, check=False).returncode == 0


def is_ancestor(repo, sha, ref):
    return git_ok(repo, "merge-base", "--is-ancestor", sha, ref)


def common_dir(repo):
    return Path(git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")).resolve()


def worktrees(repo):
    """Parse `git worktree list --porcelain` into plain dictionaries."""
    rows, current = [], None
    for line in git(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            current = {"path": Path(line[9:]).resolve(), "branch": None, "head": None,
                       "bare": False, "locked": False, "prunable": False}
            rows.append(current)
        elif current is None:
            continue
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:]
        elif line == "bare":
            current["bare"] = True
        elif line.startswith("locked"):
            current["locked"] = True
        elif line.startswith("prunable"):
            current["prunable"] = True
    return rows


def worktree_git_dir(path):
    return Path(git(path, "rev-parse", "--absolute-git-dir")).resolve()


def writer_activity(path, active_minutes, session_dir=None):
    """Git state and fresh writes are hard signals; an open session alone is not.

    Git locks, in-progress operations and recent writes block the sweep. A Pi
    transcript that merely mentions the path is a *warning*: an open session or a cwd
    inside a worktree does not by itself make the checkout busy, but it is reported so
    the sweep can combine it with uncommitted work. Unreadable metadata stays
    `unknown`, never silently abandoned.
    """
    path = Path(path)
    reasons, notes, level = [], [], "idle"
    try:
        directory = worktree_git_dir(path)
    except (Blocked, OSError, subprocess.SubprocessError):
        return {"level": "unknown", "reasons": ["unreadable worktree metadata"]}
    if (directory / "index.lock").exists():
        reasons.append("index.lock present")
    for name in GIT_OPERATIONS:
        if (directory / name).exists():
            reasons.append(f"Git operation in progress ({name})")
    for name in ("rebase-merge", "rebase-apply"):
        if (directory / name).is_dir():
            reasons.append(f"Git operation in progress ({name})")
    window = active_minutes * 60
    newest = newest_write(path)
    if newest is not None and time.time() - newest <= window:
        reasons.append(f"worktree written {int(time.time() - newest)}s ago")
    session = session_reference(path, window, session_dir)
    if session:
        notes.append(f"open Pi session {session}")
    if reasons:
        level = "busy"
    elif notes:
        level = "warning"
    return {"level": level, "reasons": reasons + notes}


def newest_write(root):
    """Bounded newest-mtime probe; a full recursive stat of a big repo would be slow."""
    newest, seen, deadline = None, 0, time.monotonic() + 5
    stack = [Path(root)]
    while stack:
        directory = stack.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError:
            continue
        for entry in entries:
            seen += 1
            if seen > MAX_SCAN_FILES or time.monotonic() > deadline:
                return newest
            if entry.name in (".git", "node_modules", ".venv", "venv"):
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                    continue
                modified = entry.stat(follow_symlinks=False).st_mtime
            except OSError:
                continue
            if newest is None or modified > newest:
                newest = modified
    return newest


def session_reference(path, window, session_dir=None):
    """Return the newest *other* Pi transcript that mentions this path, if it is recent.

    The sweep's own transcript names every checkout it inspects, so counting itself
    would make the command refuse work that nobody else is doing.
    """
    root = Path(session_dir or os.environ.get("MEGAI_PI_SESSIONS", Path.home() / ".pi/agent/sessions"))
    if not root.is_dir():
        return None
    own = os.environ.get("PI_SESSION_FILE")
    own_name = Path(own).name if own else None
    needles = {str(path), str(path).replace(str(Path.home()), "~")}
    candidates = []
    for entry in root.rglob("*.jsonl"):
        if own_name and entry.name == own_name:
            continue
        try:
            modified = entry.stat().st_mtime
        except OSError:
            continue
        if time.time() - modified <= max(window, 3600):
            candidates.append((modified, entry))
    for _, entry in sorted(candidates, reverse=True)[:12]:
        try:
            with entry.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - 400_000))
                blob = handle.read().decode("utf-8", "replace")
        except OSError:
            continue
        if any(needle in blob for needle in needles):
            return entry.name
    return None


def fetch_dev(repo, remote, branch="dev"):
    """Fetch exactly one branch; a failed fetch keeps the sweep on the last seen SHA."""
    result = git(repo, "fetch", "--no-tags", remote,
                 f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}", check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return {"ok": False, "error": detail[-1] if detail else "fetch failed"}
    return {"ok": True, "sha": git(repo, "rev-parse", f"refs/remotes/{remote}/{branch}")}


def dirty_entries(path):
    out = git(path, "status", "--porcelain=v1", "--untracked-files=all", "-z")
    return [entry for entry in out.split("\0") if entry.strip()]


def ignored_entries(path):
    result = git(path, "status", "--porcelain=v1", "--ignored=matching", "--untracked-files=all", "-z", check=False)
    if result.returncode:
        return []
    return [entry[3:] for entry in result.stdout.split("\0") if entry.startswith("!! ")]


def branch_candidates(repo, protected, prefixes):
    """Local branches that are task work, never protected or unrelated history."""
    names = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
    linked = {row["branch"][len("refs/heads/"):] for row in worktrees(repo) if row["branch"]}
    rows = []
    for name in names:
        if not name or name in protected:
            continue
        if name.startswith(prefixes) or name in linked:
            rows.append(name)
    return rows


def task_number(branch, project_prefixes):
    """`task/megai-151-slug` -> 151 when the slug names this Plane project."""
    parts = branch.split("/", 1)[-1]
    match = re.match(r"([A-Za-z0-9]+)-([1-9][0-9]*)(?:-|$)", parts)
    if not match:
        return None
    if project_prefixes and match[1].casefold() not in project_prefixes:
        return None
    return int(match[2])


def backup_ignored(path, branch, backup_root):
    """Copy ignored data out before a worktree is removed; never silently drop it."""
    entries = ignored_entries(path)
    if not entries:
        return {"path": None, "files": 0, "skipped": []}
    target = Path(backup_root) / f"mdev-{branch.replace('/', '-')}-{time.strftime('%Y%m%dT%H%M%S')}"
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    copied, skipped, total = [], [], 0
    for relative in entries:
        source = Path(path) / relative
        if not source.is_file():
            continue
        try:
            size = source.stat().st_size
        except OSError:
            continue
        if size > MAX_SINGLE_BACKUP or total + size > MAX_BACKUP_BYTES:
            skipped.append(relative)
            continue
        destination = target / "ignored" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(relative)
        total += size
    (target / "inventory.json").write_text(
        json.dumps({"branch": branch, "copied": copied, "skipped": skipped}, indent=2) + "\n"
    )
    return {"path": str(target), "files": len(copied), "skipped": skipped}


def adopt(repo, row, backup_root, message_suffix=""):
    """Commit abandoned work onto its own branch so nothing is lost or left dirty."""
    path = row["worktree"]
    if not path:
        return row
    entries = dirty_entries(path)
    if not entries:
        return row
    target = Path(backup_root) / f"mdev-wip-{row['branch'].replace('/', '-')}-{time.strftime('%Y%m%dT%H%M%S')}"
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    (target / "status.txt").write_text("\n".join(entries) + "\n")
    patch = git(path, "diff", "HEAD", check=False)
    (target / "tracked.patch").write_text(patch.stdout)
    git(path, "add", "-A", "--", ".")
    body = (
        "chore(task): adopt uncommitted work before delivery\n\n"
        f"Adopted by /mdev from {path} for branch {row['branch']}.\n"
        f"Private pre-adoption backup: {target}\n{message_suffix}".strip()
        + "\n"
    )
    git(path, "-c", "user.name=MEGAI /mdev", "-c", "user.email=mdev@megai.invalid",
        "commit", "--no-verify", "-m", body)
    row["sha"] = git(path, "rev-parse", "HEAD")
    row["adopted"] = {"backup": str(target), "entries": len(entries)}
    if dirty_entries(path):
        raise Blocked("adopted work did not commit cleanly")
    return row


def merge_into_dev(target, sha, verify_command):
    """Merge one exact SHA; roll dev back when the post-merge check fails."""
    before = git(target, "rev-parse", "HEAD")
    result = git(target, "merge", "--no-ff", "--no-edit", "--no-overwrite-ignore", sha, check=False)
    if result.returncode:
        git(target, "merge", "--abort", check=False)
        detail = (result.stdout + result.stderr).strip().splitlines()
        raise Blocked(f"merge conflict: {detail[-1] if detail else 'merge failed'}")
    merged = git(target, "rev-parse", "HEAD")
    if not is_ancestor(target, sha, merged):
        raise Blocked("merge did not include the candidate SHA")
    if not verify_command:
        return {"before": before, "merged": merged, "check": None}
    check = run_check(target, merged, verify_command)
    if not check["ok"]:
        if git(target, "rev-parse", "HEAD") != merged or dirty_entries(target):
            raise Blocked("post-merge check failed and dev changed concurrently; left for review")
        parents = git(target, "rev-list", "--parents", "-n", "1", merged).split()
        if len(parents) < 3 or parents[1] != before:
            raise Blocked("post-merge rollback target is ambiguous; left for review")
        git(target, "reset", "--hard", before)
        raise Blocked(f"post-merge check failed; dev restored: {check['output'][:400]}")
    return {"before": before, "merged": merged, "check": check}


def run_check(repo, sha, command):
    """Run the focused check on a detached worktree of the merged tree."""
    parent = tempfile.mkdtemp(prefix="megai-mdev-check.")
    path = Path(parent) / "worktree"
    try:
        git(repo, "worktree", "add", "-q", "--detach", str(path), sha)
        result = subprocess.run(
            ["/bin/sh", "-lc", command], cwd=path, capture_output=True, text=True, timeout=3600
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()[-MAX_LOG:]
        return {"ok": result.returncode == 0, "exit": result.returncode, "output": output,
                "command": command}
    finally:
        git(repo, "worktree", "remove", "--force", str(path), check=False)
        shutil.rmtree(parent, ignore_errors=True)
        git(repo, "worktree", "prune", check=False)


def push_dev(target, repo, remote, sha):
    """Non-force push of one branch, then both advertised and fetched verification."""
    result = git(target, "push", remote, "refs/heads/dev:refs/heads/dev", check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise Blocked(f"push rejected: {detail[-1] if detail else 'push failed'}")
    advertised = ls_remote(repo, remote, "refs/heads/dev")
    if advertised != sha:
        raise Blocked(f"advertised dev {advertised} != pushed {sha}")
    fetched = fetch_dev(repo, remote)
    if not fetched["ok"] or fetched["sha"] != sha:
        raise Blocked("fetched dev disagrees with the advertised tip")
    return {"remote": remote, "sha": sha, "advertised": advertised, "fetched": fetched["sha"]}


def ls_remote(repo, remote, ref):
    out = git(repo, "ls-remote", remote, ref).split()
    return out[0] if out else None


def remove_resource(repo, row, backup_root, target_branch="dev", active_minutes=ACTIVE_MINUTES):
    """Remove one task worktree/branch only with fresh, complete ownership evidence."""
    branch, path = row["branch"], row["worktree"]
    ref = f"refs/heads/{branch}"
    if not git_ok(repo, "show-ref", "--verify", "--quiet", ref):
        return {"removed": False, "reason": "branch already absent"}
    if not is_ancestor(repo, ref, target_branch) and git(repo, "rev-parse", ref) != git(repo, "rev-parse", target_branch):
        return {"removed": False, "reason": "branch is not merged into the delivered target"}
    activity = writer_activity(path, active_minutes) if path else {"level": "idle", "reasons": []}
    if activity["level"] != "idle":
        return {"removed": False, "reason": f"writer signal: {', '.join(activity['reasons'])}"}
    backup = None
    if path:
        entries = dirty_entries(path)
        if entries:
            return {"removed": False, "reason": f"{len(entries)} uncommitted change(s) retained"}
        backup = backup_ignored(path, branch, backup_root)
        result = git(repo, "worktree", "remove", path, check=False)
        if result.returncode:
            detail = (result.stderr or result.stdout).strip().splitlines()
            return {"removed": False, "reason": f"worktree remove refused: {detail[-1] if detail else 'unknown'}"}
        if any(Path(w["path"]) == Path(path) for w in worktrees(repo)) or Path(path).exists():
            return {"removed": False, "reason": "worktree removal could not be verified"}
    result = git(repo, "branch", "-d", branch, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return {"removed": False, "reason": f"branch delete refused: {detail[-1] if detail else 'unknown'}",
                "worktree_removed": bool(path), "backup": backup}
    if git_ok(repo, "show-ref", "--verify", "--quiet", ref):
        return {"removed": False, "reason": "branch deletion could not be verified"}
    git(repo, "worktree", "prune", check=False)
    return {"removed": True, "worktree": path, "branch": branch, "backup": backup}


def state_dir(override=None):
    root = Path(override or os.environ.get("MEGAI_DELIVERY_STATE", Path.home() / ".megai/state/delivery"))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def backup_root(override=None):
    root = Path(override or os.environ.get("MEGAI_BACKUP_ROOT", Path.home() / ".megai/backups"))
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def lock_target(repo):
    """One writer per target: mkdir lock next to the Git common dir, stale-safe."""
    return common_dir(repo) / "megai-mdev.lock"


def acquire(repo):
    lock = lock_target(repo)
    for _ in range(2):
        try:
            lock.mkdir()
        except FileExistsError:
            pid = lock / "pid"
            alive = False
            try:
                alive = pid.exists() and os.kill(int(pid.read_text().strip()), 0) is None
            except (OSError, ValueError):
                alive = False
            if alive:
                raise Blocked(f"another /mdev owner holds {lock}")
            shutil.rmtree(lock, ignore_errors=True)
            continue
        (lock / "pid").write_text(f"{os.getpid()}\n")
        return lock
    raise Blocked(f"could not acquire {lock}")


def release(lock):
    shutil.rmtree(lock, ignore_errors=True)


def journal(state, entry):
    pending = state / "pending"
    pending.mkdir(parents=True, exist_ok=True, mode=0o700)
    # The branch keeps two journals for the same commit/id apart; a replay is per branch.
    branch = str(entry.get("branch") or "unknown").replace("/", "-")
    name = f"{entry['sha'][:12]}-{branch}.json"
    path = pending / name
    path.write_text(json.dumps(entry, indent=2) + "\n")
    os.chmod(path, 0o600)
    return str(path)


def pending_entries(state):
    pending = state / "pending"
    if not pending.is_dir():
        return []
    rows = []
    for path in sorted(pending.glob("*.json")):
        try:
            rows.append((path, json.loads(path.read_text())))
        except (OSError, ValueError):
            continue
    return rows


def project_identity(plane, ctx, state):
    """Plane identity is best effort: a timeout must not stop the Git sweep."""
    try:
        project = plane.unique(plane.pages("project"), ctx["planeProject"])
    except Exception as error:  # any transport/API failure degrades, never aborts
        return {"ok": False, "error": str(error), "name": ctx["planeProject"]}, state
    identity = {"ok": True, "project_id": project["id"], "name": project["name"],
                "identifier": project.get("identifier"), "inReview": None}
    try:
        identity["inReview"] = plane.states(project["id"])["In Review"]
    except Exception as error:  # state lookup is an optimisation, not a requirement
        identity["statesError"] = str(error)
    return identity, state


def row_for(repo, worktree, branch, base, opts):
    row = {"repository": str(repo), "branch": branch, "worktree": worktree, "sha": None,
           "base": base, "ahead": None, "behind": None, "merged": False, "dirty": 0,
           "ignored": 0, "activity": {"level": "idle", "reasons": []}, "task": None}
    try:
        row["sha"] = git(repo, "rev-parse", f"refs/heads/{branch}")
    except Blocked as error:
        row["error"] = str(error)
        return row
    if base:
        counts = git(repo, "rev-list", "--left-right", "--count", f"{base}...{row['sha']}").split()
        row["behind"], row["ahead"] = int(counts[0]), int(counts[1])
        row["merged"] = is_ancestor(repo, row["sha"], base)
    if worktree:
        row["dirty"] = len(dirty_entries(worktree))
        row["ignored"] = len(ignored_entries(worktree))
        activity = writer_activity(worktree, opts["active_minutes"])
        if activity["level"] == "warning" and row["dirty"]:
            activity["level"] = "busy"
            activity["reasons"].append(
                "uncommitted work in a checkout referenced by an open session"
            )
        row["activity"] = activity
    row["task"] = task_number(branch, opts["project_prefixes"])
    return row


def scan(plane, ctx, opts):
    identity, state = project_identity(plane, ctx, state_dir(opts.get("state")))
    opts = dict(opts, project_prefixes=_prefixes(identity, ctx))
    prefixes = tuple(opts.get("prefixes") or TASK_PREFIXES)
    protected = set(PROTECTED) | set(ctx.get("persistentBranches") or [])
    for branches in (ctx.get("preserveBranches") or {}).values():
        protected.update(branches or [])
    report = {"project": identity, "repositories": [], "state": str(state)}
    for name in ctx["repositories"]:
        repo = Path(name)
        if not (repo / ".git").exists():
            report["repositories"].append({"path": name, "blocked": "missing repository"})
            continue
        fetched = fetch_dev(repo, opts["remote"])
        local_dev = git(repo, "rev-parse", "refs/heads/dev", check=False).stdout.strip() or None
        base = fetched.get("sha") or local_dev
        worktree_map = {}
        for item in worktrees(repo):
            if item["branch"] and not item["bare"]:
                worktree_map[item["branch"][len("refs/heads/"):]] = item
        rows = []
        for branch in branch_candidates(repo, protected, prefixes):
            item = worktree_map.get(branch)
            rows.append(row_for(repo, str(item["path"]) if item else None, branch, base, opts))
        report["repositories"].append({
            "path": name, "remote": opts["remote"], "fetch": fetched, "localDev": local_dev,
            "remoteDev": fetched.get("sha"), "base": base,
            "ahead": _ahead(repo, base, local_dev), "rows": rows,
        })
    return report


def _ahead(repo, base, local):
    if not base or not local:
        return None
    counts = git(repo, "rev-list", "--left-right", "--count", f"{base}...{local}").split()
    return {"behind": int(counts[0]), "ahead": int(counts[1])}


def evidence_text(row, delivered, remote, check, when):
    lines = [
        "MEGAI /mdev task delivery",
        f"Task: {row.get('task') or 'unresolved'} / branch {row['branch']}",
        f"Repository: {row['repository']}",
        f"Candidate commit: {row['sha']}",
        f"Delivered dev commit: {delivered}",
        f"Remote: {remote} (verified by ls-remote and re-fetch)",
        f"Branch state: {row['ahead']} ahead / {row['behind']} behind the fetched dev before merge",
        f"Worktree: {row['worktree'] or 'none'}; uncommitted before adoption: {row['dirty']}; ignored: {row['ignored']}",
        f"Source-current checks: {check['command'] if check else 'none configured'} -> "
        f"{'PASS' if check and check['ok'] else 'FAIL' if check else 'not run'}",
        f"Verified at: {when}",
    ]
    if check and check.get("output"):
        lines.append("Check output tail: " + check["output"][-1200:].replace("\n", " | "))
    if row.get("adopted"):
        lines.append(f"Adopted abandoned work; private pre-adoption backup: {row['adopted']['backup']}")
    lines.append("Parent self-review: performed by the /mdev owner over the complete delivered diff.")
    return "\n".join(lines)


def closed_states(plane, identity):
    """Plane states whose work is already finished: Done and Cancelled need no proof."""
    cached = identity.get("closed")
    if cached is not None:
        return cached
    closed = []
    try:
        rows = plane.pages("state", project_id=identity.get("project_id"))
        closed = sorted(row["id"] for row in rows
                        if str(row.get("group") or "").lower() in ("completed", "cancelled"))
    except Exception:  # identity stays best effort; the boundary re-checks its own state
        closed = []
    identity["closed"] = closed  # a list, because the sweep report is printed as JSON
    return set(closed)


def handoff(plane, identity, state, row, delivered, remote, check, report):
    """Prove the work on its Plane task; journal instead of stopping when Plane is down.

    Plane review evidence is written once per task: re-running the sweep skips a task
    already In Review so a repeated /mdev cannot inflate task descriptions.
    """
    when = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    evidence = evidence_text(row, delivered, remote, check, when)
    receipt = {"project_id": identity.get("project_id"), "task_id": None,
               "repositories": [{"path": row["repository"],
                                 "commit": row.get("merge_sha") or row["sha"],
                                 "remote": remote}]}
    if not identity.get("ok") or not row.get("task"):
        reason = ("Plane unreachable" if not identity.get("ok")
                  else "branch name carries no Plane task number")
        if not identity.get("ok"):
            entry = {"project_id": None, "task_id": None, "sha": delivered,
                     "repository": row["repository"], "branch": row["branch"],
                     "reason": reason, "created_at": when, "receipt": receipt,
                     "evidence": evidence}
            report["pending_plane"].append({"branch": row["branch"],
                                            "journal": journal(state, entry), "reason": reason})
        else:
            report["retained"].append({"branch": row["branch"], "repository": row["repository"],
                                       "reason": reason + "; delivery is recorded in this sweep report"})
        return
    try:
        items = plane.pages("workitem", project_id=identity["project_id"])
        matches = [item for item in items if item.get("sequence_id") == row["task"]]
        if len(matches) != 1:
            raise Blocked(f"task MEGAI-{row['task']} is missing or ambiguous in Plane")
        task = matches[0]
        if task.get("state") in closed_states(plane, identity):
            report["plane"].append({"branch": row["branch"], "task": row["task"],
                                    "state": "closed", "id": task["id"],
                                    "skipped": "task is already closed in Plane; nothing to prove"})
            return
        if identity.get("inReview") and task.get("state") == identity["inReview"]:
            report["plane"].append({"branch": row["branch"], "task": row["task"],
                                    "state": "In Review", "id": task["id"],
                                    "skipped": "already proven and In Review"})
            return
        receipt = dict(receipt, task_id=task["id"])
        result = plane.review_boundary(identity["project_id"], task["id"], receipt, evidence)
        report["plane"].append({"branch": row["branch"], "task": task.get("sequence_id"),
                                "state": result.get("state"), "id": task["id"]})
    except Exception as error:  # keep sweeping; replay later with `resume`
        message = str(error)
        entry = {"project_id": identity.get("project_id"), "task_id": None,
                 "sha": delivered, "repository": row["repository"], "branch": row["branch"],
                 "reason": message, "created_at": when, "receipt": receipt,
                 "evidence": evidence}
        report["pending_plane"].append({"branch": row["branch"], "journal": journal(state, entry),
                                        "reason": message})
        report["retained"].append({"branch": row["branch"], "repository": row["repository"],
                                   "reason": f"Plane hand-off deferred: {message}"})


def target_signals(path):
    """Real Git mutation signals on the shared target; reads and open sessions are not.

    The dev checkout is normally the operator's own directory, so a recent fetch, merge
    or file read must never look like a competing writer. Locks and in-progress
    operations still block, because they mean another process is mutating this target
    right now.
    """
    directory = worktree_git_dir(path)
    signals = []
    for name in ("index.lock", "HEAD.lock"):
        if (directory / name).exists():
            signals.append(f"{name} present")
    for name in GIT_OPERATIONS:
        if (directory / name).exists():
            signals.append(f"Git operation in progress ({name})")
    for name in ("rebase-merge", "rebase-apply"):
        if (directory / name).is_dir():
            signals.append(f"Git operation in progress ({name})")
    return signals


def resolve_target(repo, opts, need):
    """Find (or create) the single checkout where dev can be advanced."""
    worktree = next((w for w in worktrees(repo) if w["branch"] == "refs/heads/dev"), None)
    if worktree:
        if dirty_entries(worktree["path"]):
            raise Blocked(f"dev checkout {worktree['path']} is dirty; never overwrite it")
        signals = target_signals(worktree["path"])
        if signals:
            raise Blocked(f"dev checkout {worktree['path']} is mid-operation: "
                          + ", ".join(signals))
        return worktree["path"], None
    if not need:
        return Path(repo), None
    if not git_ok(repo, "show-ref", "--verify", "--quiet", "refs/heads/dev"):
        if not git_ok(repo, "show-ref", "--verify", "--quiet", f"refs/remotes/{opts['remote']}/dev"):
            raise Blocked("no local dev and no fetched remote dev; nothing to advance")
        git(repo, "branch", "--track", "dev", f"{opts['remote']}/dev")
    parent = Path(tempfile.mkdtemp(prefix="megai-mdev-target."))
    target = parent / "target"
    git(repo, "worktree", "add", "-q", str(target), "dev")
    return target, parent


def run(plane, ctx, opts):
    state = state_dir(opts.get("state"))
    backups = backup_root(opts.get("backups"))
    identity, _ = project_identity(plane, ctx, state)
    prefixes = tuple(opts.get("prefixes") or TASK_PREFIXES)
    protected = set(PROTECTED) | set(ctx.get("persistentBranches") or [])
    for branches in (ctx.get("preserveBranches") or {}).values():
        protected.update(branches or [])
    opts = dict(opts, project_prefixes=_prefixes(identity, ctx))
    report = {"project": identity, "state": str(state), "dryRun": bool(opts.get("dry_run")),
              "merged": [], "adopted": [], "plane": [], "pending_plane": [], "retained": [],
              "resources": [], "pushed": [], "repositories": []}
    for name in ctx["repositories"]:
        repo = Path(name)
        entry = {"path": name, "rows": [], "pushed": None, "blocked": None}
        report["repositories"].append(entry)
        if not (repo / ".git").exists():
            entry["blocked"] = "missing repository"
            continue
        try:
            _sweep_repository(plane, identity, state, backups, repo, opts, prefixes,
                              protected, entry, report)
        except Blocked as error:
            entry["blocked"] = str(error)
            report["retained"].append({"repository": name, "reason": str(error)})
    return report


def _prefixes(identity, ctx):
    names = {ctx.get("planeProject", "").casefold()}
    if identity.get("identifier"):
        names.add(str(identity["identifier"]).casefold())
    if identity.get("name"):
        names.add(str(identity["name"]).casefold())
    return names


def _sweep_repository(plane, identity, state, backups, repo, opts, prefixes, protected, entry, report):
    """One repository: adopt, merge, verify, push, prove, retire -- each step fail-soft."""
    fetched = fetch_dev(repo, opts["remote"])
    entry["fetch"] = fetched
    local_dev = git(repo, "rev-parse", "refs/heads/dev", check=False).stdout.strip() or None
    base = fetched.get("sha") or local_dev
    entry["base"] = base
    worktree_map = {}
    for item in worktrees(repo):
        if item["branch"] and not item["bare"]:
            worktree_map[item["branch"][len("refs/heads/"):]] = item
    row_opts = dict(opts, prefixes=prefixes)
    rows = [row_for(repo, str(worktree_map[b]["path"]) if b in worktree_map else None, b, base, row_opts)
            for b in branch_candidates(repo, protected, prefixes)]
    entry["rows"] = rows
    if opts.get("dry_run"):
        return
    needs_push = bool(base and local_dev and local_dev != base)
    if not rows and not needs_push:
        return
    lock = acquire(repo)
    created = None
    try:
        target, created = resolve_target(repo, opts, need=True)
        if opts.get("adopt", True):
            for row in rows:
                if row.get("error") or not row["dirty"]:
                    continue
                _adopt_row(repo, row, backups, report)
        for row in sorted((row for row in rows if not row["merged"] and not row.get("error")),
                          key=lambda item: (item["task"] or 0, item["sha"])):
            if row["dirty"]:
                report["retained"].append({"branch": row["branch"], "repository": str(repo),
                                           "reason": f"{row['dirty']} uncommitted change(s) left in place"})
                continue
            if row["worktree"] and row["activity"]["level"] in ("busy", "unknown"):
                report["retained"].append({"branch": row["branch"], "repository": str(repo),
                                           "reason": "active or unknown writer: "
                                                     + ", ".join(row["activity"]["reasons"])})
                continue
            try:
                result = merge_into_dev(target, row["sha"], opts.get("check"))
                row["merge_sha"] = result["merged"]
                row["check"] = result["check"]
                row["merged"] = True
                report["merged"].append({"branch": row["branch"], "repository": str(repo),
                                         "task": row["task"],
                                         "sha": row["sha"], "merge": result["merged"]})
            except Blocked as error:
                report["retained"].append({"branch": row["branch"], "repository": str(repo),
                                           "reason": f"merge refused: {error}"})
        tip = git(target, "rev-parse", "HEAD")
        entry["tip"] = tip
        delivered = None
        if opts.get("push", True) and tip != (fetched.get("sha") or ""):
            try:
                delivered = push_dev(target, repo, opts["remote"], tip)
                entry["pushed"] = delivered
                report["pushed"].append({"repository": str(repo), **delivered})
            except Blocked as error:
                entry["blocked"] = f"push not verified: {error}"
                report["retained"].append({"repository": str(repo),
                                           "reason": f"push not verified: {error}"})
        elif fetched.get("ok") and tip == fetched.get("sha"):
            delivered = {"remote": opts["remote"], "sha": tip, "advertised": tip, "fetched": tip}
        if not delivered:
            return
        for row in rows:
            if row["merged"] and not row.get("error"):
                handoff(plane, identity, state, row, delivered["sha"], opts["remote"],
                        row.get("check"), report)
        # A journaled hand-off keeps its worktree until Plane proves the task; only a
        # fully proven row is retired, so no evidence can disappear from under a retry.
        deferred = {entry["branch"] for entry in report["pending_plane"]}
        if opts.get("retire", True):
            for row in rows:
                if not row["merged"] or row["dirty"]:
                    continue
                if row["branch"] in deferred:
                    report["resources"].append({"branch": row["branch"], "repository": str(repo),
                                                "removed": False,
                                                "reason": "retained until the Plane hand-off is proven"})
                    continue
                outcome = remove_resource(repo, row, backups, target_branch="dev",
                                          active_minutes=opts["active_minutes"])
                report["resources"].append({"branch": row["branch"], "repository": str(repo),
                                            **outcome})
    finally:
        if created:
            git(repo, "worktree", "remove", "--force", str(created / "target"), check=False)
            shutil.rmtree(created, ignore_errors=True)
        release(lock)
    git(repo, "worktree", "prune", check=False)


def _adopt_row(repo, row, backups, report):
    """Adopt one inactive dirty checkout, then re-derive whether it still needs a merge."""
    if not row["worktree"]:
        report["retained"].append({"branch": row["branch"], "repository": str(repo),
                                   "reason": "uncommitted work outside a registered worktree"})
        return
    if row["activity"]["level"] in ("busy", "unknown"):
        report["retained"].append({"branch": row["branch"], "repository": str(repo),
                                   "reason": "active or unknown writer: "
                                             + ", ".join(row["activity"]["reasons"])})
        return
    try:
        adopt(repo, row, backups)
    except Blocked as error:
        report["retained"].append({"branch": row["branch"], "repository": str(repo),
                                   "reason": f"adoption refused: {error}"})
        return
    report["adopted"].append({"branch": row["branch"], "repository": str(repo),
                              "sha": row["sha"], "backup": row["adopted"]["backup"]})
    row["dirty"] = 0
    row["merged"] = bool(row.get("base") and is_ancestor(repo, row["sha"], row["base"]))


def resume(plane, ctx, opts):
    """Replay journaled Plane hand-offs once connectivity returns."""
    state = state_dir(opts.get("state"))
    identity, _ = project_identity(plane, ctx, state)
    report = {"project": identity, "replayed": [], "pending": []}
    for path, entry in pending_entries(state):
        if not identity.get("ok"):
            report["pending"].append({"journal": str(path), "reason": "Plane still unreachable"})
            continue
        try:
            items = plane.pages("workitem", project_id=identity["project_id"])
            if entry.get("task_id"):
                task = next((item for item in items if item.get("id") == entry["task_id"]), None)
            else:
                number = task_number(entry.get("branch") or "", _prefixes(identity, ctx))
                matches = [item for item in items if item.get("sequence_id") == number]
                task = matches[0] if len(matches) == 1 else None
            if task is None:
                raise Blocked(f"task for {entry.get('branch')} is missing or ambiguous")
            if task.get("state") in closed_states(plane, identity):
                path.unlink()
                report["replayed"].append({"journal": str(path), "branch": entry.get("branch"),
                                           "state": "closed",
                                           "dropped": "task is already closed in Plane"})
                continue
            task_id = task["id"]
            receipt = dict(entry.get("receipt") or {}, project_id=identity["project_id"], task_id=task_id)
            result = plane.review_boundary(identity["project_id"], task_id, receipt, entry["evidence"])
            path.unlink()
            report["replayed"].append({"journal": str(path), "branch": entry.get("branch"),
                                       "state": result.get("state")})
        except Exception as error:  # noqa: BLE001 - keep the journal until it succeeds
            report["pending"].append({"journal": str(path), "reason": str(error)})
    return report


def detect_forge(url, configured=None):
    if configured in ("github", "gitlab"):
        return configured
    lowered = (url or "").lower()
    if "github" in lowered:
        return "github"
    if "gitlab" in lowered:
        return "gitlab"
    return None


def forge_binary(forge):
    return {"github": "gh", "gitlab": "glab"}.get(forge or "")


def run_argv(argv, cwd, timeout=300):
    result = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def open_request(forge, repo, base, head, runner):
    """Return the single open base<-head request, or None; ambiguity is an error."""
    if forge == "github":
        code, out, err = runner(
            ["gh", "pr", "list", "--base", base, "--head", head, "--state", "open",
             "--json", "url,number,headRefOid,baseRefOid"], repo)
        if code:
            raise Blocked(f"PR lookup failed: {err or out}")
        rows = json.loads(out or "[]")
        if len(rows) > 1:
            raise Blocked("multiple open PRs for dev->main; resolve the ambiguity")
        return rows[0] if rows else None
    code, out, err = runner(
        ["glab", "mr", "list", "--source-branch", head, "--target-branch", base,
         "--output", "json"], repo)
    if code:
        raise Blocked(f"MR lookup failed: {err or out}")
    rows = [row for row in json.loads(out or "[]") if row.get("state") in (None, "opened")]
    if len(rows) > 1:
        raise Blocked("multiple open MRs for dev->main; resolve the ambiguity")
    return rows[0] if rows else None


def create_request(forge, repo, base, head, title, body_file, runner):
    if forge == "github":
        code, out, err = runner(
            ["gh", "pr", "create", "--base", base, "--head", head, "--title", title,
             "--body-file", str(body_file)], repo)
    else:
        code, out, err = runner(
            ["glab", "mr", "create", "--source-branch", head, "--target-branch", base,
             "--title", title, "--description-file", str(body_file),
             "--remove-source-branch=false", "--yes"], repo)
    if code:
        return None, f"create failed: {err or out}"
    return out, None


def pr(plane, ctx, opts):
    """Reuse or open the one dev->main request; never merge, never touch main."""
    runner = opts.get("forge_runner") or run_argv
    report = {"repositories": [], "requests": [], "noop": [], "retained": []}
    base, head = opts["base"], "dev"
    for name in ctx["repositories"]:
        repo = Path(name)
        row = {"path": name, "forge": None, "dev": None, "base": None}
        report["repositories"].append(row)
        if not (repo / ".git").exists():
            report["retained"].append({"repository": name, "reason": "missing repository"})
            continue
        remote = opts["remote"]
        try:
            row["url"] = git(repo, "remote", "get-url", remote)
        except Blocked as error:
            report["retained"].append({"repository": name, "reason": str(error)})
            continue
        forge = detect_forge(row["url"], ctx.get("forge"))
        row["forge"] = forge
        if not forge or not shutil.which(forge_binary(forge)):
            report["retained"].append({"repository": name,
                                       "reason": "no usable forge CLI for this remote"})
            continue
        fetched = git(repo, "fetch", "--no-tags", remote, f"refs/heads/{head}", f"refs/heads/{base}", check=False)
        if fetched.returncode:
            report["retained"].append({"repository": name, "reason": "remote fetch failed"})
            continue
        advertised_dev = ls_remote(repo, remote, f"refs/heads/{head}")
        advertised_base = ls_remote(repo, remote, f"refs/heads/{base}")
        row["dev"], row["base"] = advertised_dev, advertised_base
        if not advertised_base:
            report["retained"].append({"repository": name, "reason": f"remote {base} is missing"})
            continue
        if not advertised_dev:
            report["retained"].append({"repository": name, "reason": f"remote {head} is missing"})
            continue
        count = int(git(repo, "rev-list", "--count", f"{advertised_base}..{advertised_dev}"))
        row["commits"] = count
        if count == 0:
            report["noop"].append({"repository": name, "reason": f"{head} has no commits beyond {base}"})
            continue
        if opts.get("dry_run"):
            row["plan"] = f"reuse or open exactly one {head}->{base} request at {forge}"
            continue
        try:
            existing = open_request(forge, repo, base, head, runner)
        except Blocked as error:
            report["retained"].append({"repository": name, "reason": str(error)})
            continue
        if existing:
            report["requests"].append({"repository": name, "url": existing.get("url") or existing.get("web_url"),
                                       "reused": True, "head": existing.get("headRefOid"),
                                       "base": existing.get("baseRefOid")})
            continue
        body = Path(opts["body_file"]).read_text() if opts.get("body_file") else (
            f"Verified task work integrated into `{head}`.\n\n"
            + git(repo, "log", "--oneline", "--no-decorate", f"{advertised_base}..{advertised_dev}", check=False).stdout
        )
        holder = Path(tempfile.mkdtemp(prefix="megai-prdev.")) / "body.md"
        holder.write_text(body)
        try:
            url, error = create_request(forge, repo, base, head,
                                        opts.get("title") or f"Promote {head} to {base}", holder, runner)
        finally:
            shutil.rmtree(holder.parent, ignore_errors=True)
        if error:
            report["retained"].append({"repository": name, "reason": error})
            continue
        try:
            created = open_request(forge, repo, base, head, runner)
        except Blocked as error:
            report["retained"].append({"repository": name, "reason": f"uncertain create: {error}"})
            continue
        report["requests"].append({"repository": name, "url": (created or {}).get("url") or url,
                                   "reused": False, "head": (created or {}).get("headRefOid"),
                                   "base": (created or {}).get("baseRefOid")})
    return report


def main(argv, plane, defaults=None):
    import argparse

    parser = argparse.ArgumentParser(prog="pi-workflow mdev", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    for name, help_text in (
        ("scan", "read-only ledger of task branches, checkouts and writer signals"),
        ("run", "adopt, merge, verify, push, hand off and retire task branches"),
        ("resume", "replay journaled Plane hand-offs after an outage"),
        ("pr", "reuse or open the single dev->main pull request"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--cwd", default=os.getcwd())
        cmd.add_argument("--remote", default="origin")
        cmd.add_argument("--state", default=None)
        cmd.add_argument("--backups", default=None)
        cmd.add_argument("--active-minutes", type=int, default=ACTIVE_MINUTES)
        cmd.add_argument("--prefix", action="append", default=None,
                         help="task branch prefix (default task/)")
        if name == "run":
            cmd.add_argument("--check", default=None, help="focused command run on the merged tree")
            cmd.add_argument("--no-adopt", dest="adopt", action="store_false")
            cmd.add_argument("--no-push", dest="push", action="store_false")
            cmd.add_argument("--keep-resources", dest="retire", action="store_false")
            cmd.add_argument("--dry-run", action="store_true")
        elif name == "pr":
            cmd.add_argument("--base", default="main")
            cmd.add_argument("--title", default=None)
            cmd.add_argument("--body-file", default=None)
            cmd.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    options = vars(args)
    options["prefixes"] = tuple(args.prefix or TASK_PREFIXES)
    options.setdefault("adopt", False)
    options.setdefault("push", False)
    options.setdefault("retire", True)
    options.setdefault("dry_run", False)
    options.setdefault("check", None)
    options.setdefault("base", "main")
    ctx = plane.context(args.cwd)
    if args.action == "scan":
        return scan(plane, ctx, options)
    if args.action == "run":
        return run(plane, ctx, options)
    if args.action == "resume":
        return resume(plane, ctx, options)
    return pr(plane, ctx, options)
