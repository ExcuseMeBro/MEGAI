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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("context")
    cmd.add_argument("--cwd", default=os.getcwd())
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
