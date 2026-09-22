#!/usr/bin/env python3
"""Plane boundaries and repository context for the global Pi profile."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from plane_mcp_headers import read_token  # noqa: E402

ENDPOINT = "https://mcp.plane.so/http/api-key/mcp"
MARKER = r"<pre>PI_DELIVERY_V1:(.*?):END_PI_DELIVERY_V1</pre>"


def git(path, *args):
    result = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, timeout=60
    )
    if result.returncode:
        raise ValueError(f"git {args[0]} failed in {path}: {result.stderr.strip()}")
    return result.stdout.strip()


def primary(path):
    common = Path(git(path, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    if common.name != ".git":
        raise ValueError("A non-bare primary checkout is required")
    return common.parent.resolve()


def context(cwd):
    cwd = Path(cwd).resolve()
    try:
        repo = primary(cwd)
    except ValueError:
        repo = None
    anchor = repo or cwd
    boundary = Path(
        os.environ.get("PI_PROJECTS_ROOT", Path.home() / "PROJECTS")
    ).resolve()
    root, config = anchor, {}
    configs = []
    for candidate in [anchor, *anchor.parents]:
        if candidate in (boundary, Path.home(), Path("/")):
            break
        file = candidate / ".pi/project.json"
        if file.is_file():
            configs.append((candidate, json.loads(file.read_text())))
    if configs:
        root, config = configs[0]
        groups = [
            (path, value) for path, value in configs if value.get("layout") == "multi"
        ]
        if groups:
            root, config = groups[-1]  # Umbrella identity survives component overrides.
            config = dict(config)
            extras = dict(config.get("preserveBranches", {}))
            for _, value in reversed(configs):
                for name, branches in value.get("preserveBranches", {}).items():
                    extras[name] = sorted(set(extras.get(name, []) + branches))
            config["preserveBranches"] = extras
    if not config and repo and repo.parent.parent == boundary:
        root = repo.parent
    children = sorted(p for p in root.iterdir() if p.is_dir() and (p / ".git").exists())
    layout = config.get("layout", "mono" if (root / ".git").exists() else "multi")
    if layout not in ("mono", "multi"):
        raise ValueError("layout must be mono or multi")
    names = config.get(
        "repositories", ["."] if layout == "mono" else [p.name for p in children]
    )
    if not isinstance(names, list) or not names:
        raise ValueError("No repositories found; configure .pi/project.json")
    repositories = []
    for name in names:
        if not isinstance(name, str):
            raise ValueError("Repository paths must be strings")
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not (path / ".git").exists():
            raise ValueError(f"Repository must exist within project: {name}")
        repositories.append(str(path))
    if repo and str(repo) not in repositories:
        raise ValueError(
            "Current repository is absent from local project configuration"
        )
    rules = []
    for path in (
        root / "AGENTS.md",
        *(Path(p) / "AGENTS.md" for p in repositories if not repo or p == str(repo)),
    ):
        if path.is_file() and str(path) not in rules:
            rules.append(str(path))
    if repo:
        worktree_root = Path(git(cwd, "rev-parse", "--show-toplevel"))
        for folder in reversed([cwd, *cwd.parents]):
            path = folder / "AGENTS.md"
            if (
                folder.is_relative_to(worktree_root)
                and path.is_file()
                and str(path) not in rules
            ):
                rules.append(str(path))
    return {
        "root": str(root),
        "repository": str(repo) if repo else None,
        "layout": layout,
        "repositories": repositories,
        "rules": rules,
        "planeProject": config.get("planeProject", root.name),
        "forge": config.get("forge"),
        "persistentBranches": ["dev", "main"],
        "preserveBranches": config.get("preserveBranches", {}),
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Plane redirect refused")


def call(name, arguments):
    token = read_token(str(Path.home() / ".config/megai/credentials/plane-api-token"))
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "x-workspace-slug": "brodev",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    ca = "/etc/ssl/cert.pem" if Path("/etc/ssl/cert.pem").exists() else None
    opener = urllib.request.build_opener(
        NoRedirect(),
        urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=ca)),
    )
    with opener.open(request, timeout=45) as response:
        raw = response.read(8_000_001)
    if len(raw) > 8_000_000:
        raise ValueError("Plane response exceeded limit")
    text = raw.decode()
    if text.startswith("event:") or text.startswith("data:"):
        text = next(line[6:] for line in text.splitlines() if line.startswith("data: "))
    envelope = json.loads(text)
    if "error" in envelope:
        raise ValueError("Plane RPC failed; reconcile state before retrying a write")
    result = envelope["result"]
    if result.get("isError"):
        raise ValueError(
            "Plane operation failed; reconcile state before retrying a write"
        )
    return json.loads(next(c["text"] for c in result["content"] if c["type"] == "text"))


def pages(name, **arguments):
    rows, seen = [], set()
    while True:
        page = call(name, {"action": "list", "per_page": 100, **arguments})
        if not isinstance(page.get("results"), list) or not isinstance(
            page.get("next_page_results"), bool
        ):
            raise ValueError("Incomplete Plane pagination")
        rows.extend(page["results"])
        if not page["next_page_results"]:
            return rows
        cursor = page.get("next_cursor")
        if not cursor or cursor in seen:
            raise ValueError("Invalid Plane pagination cursor")
        seen.add(cursor)
        arguments["cursor"] = cursor


def unique(rows, name):
    matches = [row for row in rows if row["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name!r}; found {len(matches)}")
    return matches[0]


def states(project):
    rows = pages("state", project_id=project)
    result = {}
    for name, group in [
        ("Todo", "unstarted"),
        ("In Progress", "started"),
        ("In Review", "started"),
        ("Done", "completed"),
    ]:
        value = unique(rows, name)
        if value["group"] != group:
            raise ValueError(f"Wrong Plane state group for {name}")
        result[name] = value["id"]
    return result


def receipt_repositories(receipt):
    repos = receipt.get("repositories")
    if not isinstance(repos, list) or not repos:
        raise ValueError("Receipt must include every affected repository")
    seen = set()
    for repo in repos:
        path = Path(repo["path"])
        sha, remote = repo["commit"], repo.get("remote", "origin")
        if not path.is_absolute() or not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError(
                "Receipt requires absolute repository paths and full commit SHAs"
            )
        canonical = primary(path)
        if canonical in seen:
            raise ValueError("Duplicate receipt repository")
        seen.add(canonical)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote):
            raise ValueError("Invalid remote name")
        git(canonical, "cat-file", "-e", f"{sha}^{{commit}}")
        url = git(canonical, "remote", "get-url", remote)
        policy = context(canonical)
        if policy["forge"] and not (
            url.startswith(f"https://{policy['forge']}/")
            or url.startswith(f"git@{policy['forge']}:")
            or url.startswith(f"ssh://git@{policy['forge']}/")
        ):
            raise ValueError("Remote violates the local forge policy")
        if repo.get("remoteUrl", url) != url:
            raise ValueError("Remote URL changed since review")
        yield canonical, sha, remote


def verify_main(receipt):
    verified = []
    for path, sha, remote in receipt_repositories(receipt):
        # Fetch one branch explicitly, then check that exact advertised main tip.
        # FETCH_HEAD avoids trusting an old remote-tracking ref after remote rewinds.
        git(path, "fetch", "--no-tags", remote, "refs/heads/main")
        tip = git(path, "rev-parse", "FETCH_HEAD^{commit}")
        git(path, "merge-base", "--is-ancestor", sha, tip)
        verified.append(
            {"path": str(path), "commit": sha, "main": tip, "remote": remote}
        )
    return verified


def _git_proc(path, *args, timeout=120):
    """Read-only Git call: no optional index locks, no opportunistic gc."""
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        return subprocess.run(
            ["git", "-C", str(path), "-c", "gc.auto=0", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"git {args[0]} unavailable: {error}")


def _paseo_json(*args):
    """Documented Paseo read command; any failure is fatal, never guessed."""
    try:
        result = subprocess.run(
            ["paseo", *args, "--json"],
            capture_output=True,
            text=True,
            timeout=45,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"Paseo {args[0]} unavailable: {error}")
    if result.returncode:
        raise ValueError(f"Paseo {' '.join(args)} failed; reconcile state")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError(f"Malformed Paseo response for {' '.join(args)}: {error}")


def _rows(payload, fields):
    if not isinstance(payload, list):
        raise ValueError("Malformed Paseo response: expected a list")
    for row in payload:
        if not isinstance(row, dict) or any(
            not isinstance(row.get(field), str) for field in fields
        ):
            raise ValueError("Malformed Paseo response: unexpected fields")
    return payload


def _expand(value):
    return os.path.realpath(os.path.expanduser(str(value)))


def _primary_or_none(path):
    try:
        return str(primary(path))
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return None


def _ancestor(path, sha, tip):
    return _git_proc(path, "merge-base", "--is-ancestor", sha, tip).returncode == 0


def _local_ref(path, name):
    result = _git_proc(path, "rev-parse", "--verify", "--quiet", f"refs/heads/{name}")
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def _ignored(path):
    result = _git_proc(path, "ls-files", "--others", "--ignored", "--exclude-standard")
    return [line for line in result.stdout.splitlines() if line] if result.returncode == 0 else []


_OPERATION_MARKERS = (
    ("merge", "MERGE_HEAD"),
    ("cherry-pick", "CHERRY_PICK_HEAD"),
    ("revert", "REVERT_HEAD"),
    ("rebase", "rebase-merge"),
    ("rebase", "rebase-apply"),
    ("bisect", "BISECT_LOG"),
)


def _git_dirs(path):
    dirs = []
    for args in (("rev-parse", "--git-dir"), ("rev-parse", "--git-common-dir")):
        result = _git_proc(path, *args)
        if result.returncode == 0 and result.stdout.strip():
            value = Path(result.stdout.strip())
            if not value.is_absolute():
                value = (Path(path) / value).resolve()
            if value not in dirs:
                dirs.append(value)
    return dirs


def _operation(path):
    for folder in _git_dirs(path):
        for name, marker in _OPERATION_MARKERS:
            if (folder / marker).exists():
                return name
    return None


def _worktree_entries(path):
    result = _git_proc(path, "worktree", "list", "--porcelain")
    if result.returncode:
        return []
    entries, current = [], None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            if current:
                entries.append(current)
            current = {
                "path": line[len("worktree "):].strip(),
                "branch": None,
                "head": None,
                "locked": False,
            }
        elif current is None:
            continue
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):].strip()
        elif line.startswith("branch "):
            ref = line[len("branch "):].strip()
            current["branch"] = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
        elif line == "detached":
            current["branch"] = None
        elif line.startswith("locked"):
            current["locked"] = True
    if current:
        entries.append(current)
    return entries


def _snapshot(path):
    refs = {}
    result = _git_proc(path, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/")
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            name, _, sha = line.partition(" ")
            if name:
                refs[f"refs:{name}"] = sha
    for entry in _worktree_entries(path):
        item = _git_proc(entry["path"], "rev-parse", "--verify", "HEAD")
        refs[f"head:{entry['path']}"] = item.stdout.strip() if item.returncode == 0 else None
    return refs


def _fetch_tip(repo, remote, branch):
    """Fetch one branch with an empty refmap so named refs are not rewritten."""
    result = _git_proc(
        repo, "fetch", "--no-tags", "--refmap=", remote, f"refs/heads/{branch}"
    )
    if result.returncode:
        return None, (result.stderr.strip() or "fetch failed")[:200]
    tip = _git_proc(repo, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
    if tip.returncode or not tip.stdout.strip():
        return None, "cannot resolve FETCH_HEAD"
    return tip.stdout.strip(), None


def _forge_allowed(url, forge):
    return (
        url.startswith(f"https://{forge}/")
        or url.startswith(f"git@{forge}:")
        or url.startswith(f"ssh://git@{forge}/")
    )


def _preserve_for(repo, root, policy):
    relative = os.path.relpath(str(repo), str(root))
    return list(policy.get("preserveBranches", {}).get(relative, []))


def _repo_row(repo, root, policy):
    blocked = []
    current_result = _git_proc(repo, "symbolic-ref", "--short", "-q", "HEAD")
    current = (
        current_result.stdout.strip()
        if current_result.returncode == 0 and current_result.stdout.strip()
        else None
    )
    head_result = _git_proc(repo, "rev-parse", "--verify", "HEAD")
    head = head_result.stdout.strip() if head_result.returncode == 0 else None
    status_result = _git_proc(repo, "status", "--porcelain=v1")
    porcelain = status_result.stdout.splitlines() if status_result.returncode == 0 else []
    untracked = [line[3:] for line in porcelain if line.startswith("?? ")]
    dirty = bool(porcelain)
    ignored = _ignored(repo)
    operation = _operation(repo)
    if dirty:
        blocked.append("dirty")
    if operation:
        blocked.append(f"operation:{operation}")
    if ignored:
        blocked.append("ignored-untracked")

    remote = "origin"
    persistent = []
    for name in ("dev", "main", *_preserve_for(repo, root, policy)):
        if name not in persistent:
            persistent.append(name)
    fetched = {}
    remote_error = None
    url_result = _git_proc(repo, "remote", "get-url", remote)
    if url_result.returncode != 0:
        remote_error = f"remote {remote} unavailable"
        blocked.append("remote-missing")
    else:
        url = url_result.stdout.strip()
        forge = policy.get("forge")
        if forge and not _forge_allowed(url, forge):
            remote_error = "remote violates forge policy"
            blocked.append("remote-forge-policy")
        else:
            for branch in persistent:
                tip, error = _fetch_tip(repo, remote, branch)
                fetched[branch] = tip
                if error:
                    blocked.append(f"fetch-failed:{branch}")
                    if branch == "dev":
                        remote_error = error
    remote_dev = fetched.get("dev")

    branch_result = _git_proc(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    names = set(persistent)
    if branch_result.returncode == 0:
        names.update(line for line in branch_result.stdout.splitlines() if line)
    branches = {}
    for name in sorted(names):
        local = _local_ref(repo, name)
        in_remote = bool(local and remote_dev and _ancestor(repo, local, remote_dev))
        branches[name] = {
            "local": local,
            "remote": fetched.get(name),
            "inRemoteDev": in_remote,
            "diverged": bool(local and remote_dev and not in_remote),
        }

    worktrees = []
    for entry in _worktree_entries(repo):
        in_remote = bool(
            entry["head"] and remote_dev and _ancestor(repo, entry["head"], remote_dev)
        )
        worktrees.append(
            {
                "path": entry["path"],
                "branch": entry["branch"],
                "head": entry["head"],
                "locked": entry["locked"],
                "inRemoteDev": in_remote,
            }
        )

    row = {
        "path": str(repo),
        "current": current,
        "head": head,
        "detached": current is None,
        "dirty": dirty,
        "untracked": untracked,
        "ignored": ignored,
        "operation": operation,
        "remoteDev": remote_dev,
        "remoteDevError": remote_error,
        "branches": branches,
        "worktrees": worktrees,
        "blocked": blocked,
    }
    return row


def status(cwd, workspace_id=None):
    policy = context(cwd)
    root = Path(policy["root"])
    repositories = [Path(path) for path in policy["repositories"]]
    repo_paths = {str(repo) for repo in repositories}
    runner = os.environ.get("PASEO_AGENT_ID")

    before = {str(repo): _snapshot(repo) for repo in repositories}
    repo_rows = [_repo_row(repo, root, policy) for repo in repositories]
    rows_by_path = {row["path"]: row for row in repo_rows}

    projects = _rows(_paseo_json("project", "ls"), ("projectId", "name", "path"))
    workspaces = _rows(
        _paseo_json("workspace", "ls"),
        ("workspaceId", "project", "name", "isolation", "cwd"),
    )
    agents = _rows(_paseo_json("agent", "ls", "--all"), ("id", "cwd", "status"))

    canon_root = _expand(root)
    matching = [p for p in projects if _expand(p["path"]) == canon_root]
    project_id = matching[0]["projectId"] if len(matching) == 1 else None
    by_name = {}
    for project in projects:
        by_name.setdefault(project["name"], []).append(project["projectId"])
    candidate_names = {project["name"] for project in matching}

    if workspace_id:
        selected = [w for w in workspaces if w["workspaceId"] == workspace_id]
        if len(selected) != 1:
            raise ValueError(f"Requested workspace {workspace_id} not found")
        requested = selected[0]
        if project_id is None or by_name.get(requested["project"], []) != [project_id]:
            raise ValueError("Requested workspace belongs to another project")
        requested_primary = _primary_or_none(_expand(requested["cwd"]))
        if requested_primary is None or requested_primary not in repo_paths:
            raise ValueError("Requested workspace is outside the resolved project")
    else:
        selected = [w for w in workspaces if w["project"] in candidate_names]

    observations = {}
    for workspace in selected:
        cwd_value = _expand(workspace["cwd"])
        matched = [a for a in agents if _expand(a["cwd"]) == cwd_value]
        inspects = []
        for item in matched:
            try:
                inspects.append((item, _paseo_json("agent", "inspect", item["id"])))
            except ValueError:
                inspects.append((item, None))
        observations[workspace["workspaceId"]] = (matched, inspects, cwd_value)

    after = {str(repo): _snapshot(repo) for repo in repositories}
    moved = {}
    for key in before:
        changed = {name for name in before[key] if after[key].get(name) != before[key][name]}
        if changed:
            moved[key] = changed
            rows_by_path[key]["blocked"].append("ref-moved")

    workspace_rows = []
    for workspace in selected:
        row = _workspace_row(
            workspace,
            policy,
            project_id,
            by_name,
            repo_paths,
            rows_by_path,
            observations[workspace["workspaceId"]],
            moved,
            runner,
        )
        workspace_rows.append(row)

    pending = []
    for row in repo_rows:
        if row["remoteDev"] is None:
            continue
        for name, info in row["branches"].items():
            if info["local"] and not info["inRemoteDev"]:
                pending.append(
                    {"kind": "branch", "path": row["path"], "branch": name,
                     "head": info["local"], "reason": "not-in-remote-dev"}
                )
        for entry in row["worktrees"]:
            if entry["head"] and not entry["inRemoteDev"]:
                pending.append(
                    {"kind": "worktree", "path": entry["path"], "branch": entry["branch"],
                     "head": entry["head"], "reason": "not-in-remote-dev"}
                )

    blocked = [
        {"scope": "repo", "id": row["path"], "reason": reason}
        for row in repo_rows
        for reason in row["blocked"]
    ] + [
        {"scope": "workspace", "id": row["workspaceId"], "reason": reason}
        for row in workspace_rows
        for reason in row["blocked"]
    ]
    cleanup = [
        {"workspaceId": row["workspaceId"], "cwd": row["cwd"], "head": row["head"]}
        for row in workspace_rows
        if row["archiveEligible"]
    ]
    return {
        "root": str(root),
        "layout": policy["layout"],
        "planeProject": policy["planeProject"],
        "repositories": repo_rows,
        "workspaces": workspace_rows,
        "pendingDelivery": pending,
        "cleanupEligible": cleanup,
        "blocked": blocked,
    }


def _workspace_row(
    workspace, policy, project_id, by_name, repo_paths, rows_by_path, observation,
    moved, runner,
):
    cwd_value = _expand(workspace["cwd"])
    matched, inspects, _ = observation
    blocked = []
    ids = by_name.get(workspace["project"], [])
    primary_path = _primary_or_none(cwd_value)
    if project_id is not None and ids == [project_id]:
        ownership = "known" if primary_path in repo_paths else "foreign"
    elif project_id is not None and ids:
        ownership = "foreign"
    else:
        ownership = "unknown"
    if ownership != "known":
        blocked.append(f"ownership-{ownership}")

    protected = any(item["id"] == runner for item in matched)
    busy = protected
    released = False
    for item, inspect in inspects:
        if inspect is None:
            blocked.append("inspect-failed")
            continue
        archived = inspect.get("Archived") is True
        permissions = inspect.get("PendingPermissions") or []
        if not archived or permissions:
            busy = True
        identity_ok = (
            inspect.get("Id") == item["id"]
            and _expand(inspect.get("Cwd", "")) == cwd_value
        )
        if archived and not permissions and identity_ok and inspect.get("Status") == "idle":
            released = True
        elif archived and (not identity_ok or inspect.get("Status") != "idle"):
            blocked.append("incomplete-terminal-evidence")
    if not matched:
        blocked.append("no-agent-release-evidence")
    if released and busy:
        released = False

    head = branch = operation = None
    dirty = False
    ignored = []
    if primary_path is not None:
        head_result = _git_proc(cwd_value, "rev-parse", "--verify", "HEAD")
        head = head_result.stdout.strip() if head_result.returncode == 0 else None
        branch_result = _git_proc(cwd_value, "symbolic-ref", "--short", "-q", "HEAD")
        branch = (
            branch_result.stdout.strip()
            if branch_result.returncode == 0 and branch_result.stdout.strip()
            else None
        )
        status_result = _git_proc(cwd_value, "status", "--porcelain=v1")
        dirty = status_result.returncode == 0 and bool(status_result.stdout.strip())
        ignored = _ignored(cwd_value)
        operation = _operation(cwd_value)

    entry = None
    repo_row = rows_by_path.get(primary_path) if primary_path else None
    if repo_row:
        entry = next((w for w in repo_row["worktrees"] if w["path"] == cwd_value), None)
    registered = entry is not None
    locked = bool(entry and entry["locked"])

    remote_dev = repo_row["remoteDev"] if repo_row else None
    in_remote = bool(head and remote_dev and _ancestor(primary_path, head, remote_dev))
    moved_here = False
    if repo_row and primary_path in moved:
        changed = moved[primary_path]
        moved_here = (
            f"head:{cwd_value}" in changed
            or (branch and f"refs:refs/heads/{branch}" in changed)
        )
    if moved_here:
        blocked.append("ref-moved")
    if not registered:
        blocked.append("worktree-not-registered")
    if locked:
        blocked.append("worktree-locked")
    if dirty:
        blocked.append("dirty")
    if ignored:
        blocked.append(f"ignored:{ignored[0]}")
    if operation:
        blocked.append(f"operation:{operation}")
    if head and remote_dev and not in_remote:
        blocked.append("not-in-remote-dev")
    if branch is None:
        blocked.append("detached-head")

    eligible = (
        ownership == "known"
        and workspace["isolation"] == "worktree"
        and registered
        and not locked
        and not busy
        and not protected
        and released
        and not dirty
        and not ignored
        and operation is None
        and branch is not None
        and head is not None
        and branch == entry["branch"]
        and in_remote
        and not moved_here
    )
    return {
        "workspaceId": workspace["workspaceId"],
        "project": workspace["project"],
        "projectId": project_id if ownership == "known" else None,
        "name": workspace["name"],
        "isolation": workspace["isolation"],
        "cwd": workspace["cwd"],
        "ownership": ownership,
        "busy": busy,
        "protected": protected,
        "released": released,
        "head": head,
        "branch": branch,
        "dirty": dirty,
        "ignored": ignored,
        "operation": operation,
        "inRemoteDev": in_remote,
        "archiveEligible": eligible,
        "blocked": blocked,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("context")
    cmd.add_argument("--cwd", default=os.getcwd())
    cmd = sub.add_parser("status")
    cmd.add_argument("--cwd", default=os.getcwd())
    cmd.add_argument("--workspace")
    cmd = sub.add_parser("start")
    cmd.add_argument("--title", required=True)
    cmd.add_argument("--cwd", default=os.getcwd())
    for name in ("review", "done"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--project-id", required=True)
        cmd.add_argument("--task-id", required=True)
        if name == "review":
            cmd.add_argument("--receipt", required=True)
            cmd.add_argument("--evidence-file", required=True)
    cmd = sub.add_parser("verify-main")
    cmd.add_argument("receipt")
    args = parser.parse_args()
    if args.command == "context":
        return context(args.cwd)
    if args.command == "status":
        return status(args.cwd, args.workspace)
    if args.command == "verify-main":
        return verify_main(json.loads(Path(args.receipt).read_text()))
    if args.command == "start":
        project = unique(pages("project"), context(args.cwd)["planeProject"])["id"]
        workflow = states(project)
        matches = [
            x for x in pages("workitem", project_id=project) if x["name"] == args.title
        ]
        if len(matches) > 1:
            raise ValueError(
                "Multiple exact task matches; select the existing task explicitly"
            )
        item = (
            matches[0]
            if matches
            else call(
                "workitem",
                {
                    "action": "create",
                    "project_id": project,
                    "name": args.title,
                    "state": workflow["Todo"],
                },
            )
        )
        if item["state"] not in (workflow["Todo"], workflow["In Progress"]):
            raise ValueError(
                "Existing task is beyond Todo/In Progress; reconcile explicitly"
            )
        if item["state"] != workflow["In Progress"]:
            item = call(
                "workitem",
                {
                    "action": "update",
                    "project_id": project,
                    "workitem_id": item["id"],
                    "state": workflow["In Progress"],
                },
            )
        if item["state"] != workflow["In Progress"]:
            raise ValueError("Plane did not confirm In Progress")
        return {"project_id": project, "task_id": item["id"], "state": "In Progress"}
    project, task = args.project_id, args.task_id
    workflow = states(project)
    item = call(
        "workitem", {"action": "retrieve", "project_id": project, "workitem_id": task}
    )
    description = item.get("description_html") or ""
    original_description = description
    original_state = item["state"]
    if args.command == "review":
        if item["state"] not in (workflow["In Progress"], workflow["In Review"]):
            raise ValueError("Review requires In Progress or In Review")
        receipt = json.loads(Path(args.receipt).read_text())
        if (
            receipt.get("project_id", project) != project
            or receipt.get("task_id", task) != task
        ):
            raise ValueError("Receipt belongs to a different Plane task")
        project_name = call("project", {"action": "retrieve", "project_id": project})[
            "name"
        ]
        canonical_repos = []
        for path, sha, remote in receipt_repositories(receipt):
            if context(path)["planeProject"] != project_name:
                raise ValueError(
                    "Receipt repository belongs to a different Plane project"
                )
            canonical_repos.append(
                {
                    "path": str(path),
                    "commit": sha,
                    "remote": remote,
                    "remoteUrl": git(path, "remote", "get-url", remote),
                }
            )
        receipt = {
            "project_id": project,
            "task_id": task,
            "repositories": canonical_repos,
        }
        previous = re.findall(MARKER, description, flags=re.S)
        if len(previous) > 1:
            raise ValueError("Ambiguous previous receipt")
        if previous:
            old = json.loads(html.unescape(previous[0]))
            for path, sha, remote in receipt_repositories(old):
                replacement = next(
                    (r for r in canonical_repos if r["path"] == str(path)), None
                )
                if not replacement or replacement["remote"] != remote:
                    raise ValueError(
                        "Re-review cannot drop a previously affected repository"
                    )
                git(path, "merge-base", "--is-ancestor", sha, replacement["commit"])
        evidence = Path(args.evidence_file).read_text().strip()
        if not evidence:
            raise ValueError("Provide actual verification evidence")
        description = re.sub(MARKER, "", description, flags=re.S)
        description += f"<pre>{html.escape(evidence)}</pre><pre>PI_DELIVERY_V1:{html.escape(json.dumps(receipt))}:END_PI_DELIVERY_V1</pre>"
        target = "In Review"
    else:
        if item["state"] != workflow["In Review"]:
            raise ValueError("Done requires In Review")
        matches = re.findall(MARKER, description, flags=re.S)
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous reviewed delivery receipt")
        receipt = json.loads(html.unescape(matches[0]))
        if receipt.get("project_id") != project or receipt.get("task_id") != task:
            raise ValueError("Reviewed receipt belongs to a different Plane task")
        proof = verify_main(receipt)
        description += (
            f"<pre>Verified main delivery: {html.escape(json.dumps(proof))}</pre>"
        )
        target = "Done"
    latest = call(
        "workitem", {"action": "retrieve", "project_id": project, "workitem_id": task}
    )
    if (
        latest["state"] != original_state
        or (latest.get("description_html") or "") != original_description
    ):
        raise ValueError(
            "Plane item changed during verification; reconcile before retrying"
        )
    # Plane does not expose compare-and-swap. Parent owns this boundary; avoid concurrent editors.
    result = call(
        "workitem",
        {
            "action": "update",
            "project_id": project,
            "workitem_id": task,
            "state": workflow[target],
            "description_html": description,
        },
    )
    if result["state"] != workflow[target]:
        raise ValueError("Plane did not confirm the requested state")
    return {"project_id": project, "task_id": task, "state": target}


if __name__ == "__main__":
    try:
        print(json.dumps(main(), indent=2))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        sys.exit(1)
