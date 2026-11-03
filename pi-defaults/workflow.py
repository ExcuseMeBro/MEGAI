#!/usr/bin/env python3
"""Plane boundaries and repository context for the global Pi profile."""

from __future__ import annotations

import argparse
import html
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import tempfile
import shutil
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from plane_mcp_headers import tokens  # noqa: E402

# Transport failures are routine against the hosted Plane MCP endpoint. Retrying with
# backoff here is what makes /mdev and /prdev keep going instead of stopping the agent
# on the first timeout; every write in this module is an absolute-state update, so a
# replay is idempotent and never duplicates work.
REQUEST_TIMEOUT = float(os.environ.get("PI_PLANE_TIMEOUT", "30"))
ATTEMPTS = max(1, int(os.environ.get("PI_PLANE_ATTEMPTS", "5")))
AUTH_ATTEMPTS = max(1, int(os.environ.get("PI_PLANE_AUTH_ATTEMPTS", "2")))
RETRY_CAP = float(os.environ.get("PI_PLANE_RETRY_CAP", "15"))
# A throttled endpoint answers `401 invalid_token` for a key that is still valid and only
# recovers after the rate window: wait on this ladder before believing the key is dead.
AUTH_WAITS = (5.0, 15.0, 30.0)
PACE = float(os.environ.get("PI_PLANE_PACE", "0.25"))
LAST_CALL = {"at": 0.0}
TRANSIENT = re.compile(
    r"timeout|timed out|temporar|unavailable|try again|rate.?limit|too many requests|"
    r"connection|connect|reset by peer|broken pipe|handshake|network|EOF|"
    r"\b(?:500|502|503|504)\b|SSL",
    re.I,
)


class PlaneError(ValueError):
    """A Plane call failure: whether a retry can help, whether it is auth, when to retry."""

    def __init__(self, message, transient=False, auth=False, retry_after=None):
        super().__init__(message)
        self.transient = transient
        self.auth = auth
        self.retry_after = retry_after

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


TOKEN_FILE = Path.home() / ".config/megai/credentials/plane-api-token"
CREDENTIAL = {"source": None, "token": None}


def credentials():
    """Known-good credential first, then every other candidate, without duplicates."""
    known = CREDENTIAL.get("token")
    ordered = [*tokens(TOKEN_FILE)]
    if known:
        source = CREDENTIAL.get("source") or "cached credential"
        ordered = [(source, known)] + [(name, value) for name, value in ordered if value != known]
    if not ordered:
        raise PlaneError(
            f"no usable Plane credential: set PLANE_API_TOKEN, or write a token to {TOKEN_FILE}",
            auth=True,
        )
    return ordered


def error_detail(error):
    try:
        body = json.loads(error.read() or b"{}")
    except (ValueError, OSError):
        return ""
    for key in ("error_description", "error", "message"):
        value = body.get(key) if isinstance(body, dict) else None
        if isinstance(value, str) and value:
            return value
    return ""


def _call_once(name, arguments, token):
    # The hosted endpoint rates limits per client, so a burst of inventory reads must
    # not overtake itself; pacing is cheaper than discovering the limit with a 429.
    idle = PACE - (time.monotonic() - LAST_CALL["at"])
    if idle > 0:
        time.sleep(idle)
    LAST_CALL["at"] = time.monotonic()
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
    try:
        with opener.open(request, timeout=REQUEST_TIMEOUT) as response:
            raw = response.read(8_000_001)
    except urllib.error.HTTPError as error:  # a subclass of URLError: classify it first
        detail = error_detail(error)
        suffix = f": {detail}" if detail else ""
        retry_after = None
        header = error.headers.get("Retry-After") if error.headers else None
        if isinstance(header, str) and header.strip().isdigit():
            retry_after = min(float(header.strip()), 45.0)
        if error.code in (401, 403):
            raise PlaneError(f"Plane rejected the credential ({error.code}){suffix}",
                             auth=True, retry_after=retry_after) from error
        if error.code == 429 or error.code >= 500:
            raise PlaneError(f"Plane unavailable ({error.code}){suffix}", transient=True,
                             retry_after=retry_after) from error
        raise PlaneError(f"Plane request failed ({error.code}){suffix}") from error
    except (TimeoutError, urllib.error.URLError, ConnectionError, ssl.SSLError,
            http.client.HTTPException) as error:
        raise PlaneError(f"Plane unreachable: {error}", transient=True) from error
    if len(raw) > 8_000_000:
        raise PlaneError("Plane response exceeded limit")
    text = raw.decode()
    if text.startswith("event:") or text.startswith("data:"):
        data = next((line[6:] for line in text.splitlines() if line.startswith("data: ")), None)
        if data is None:
            raise PlaneError("Plane returned an unreadable event stream", transient=True)
        text = data
    try:
        envelope = json.loads(text)
    except ValueError as error:
        raise PlaneError(f"Plane returned unreadable JSON: {text[:200]}", transient=True) from error
    if "error" in envelope:
        detail = envelope["error"]
        message = detail.get("message") if isinstance(detail, dict) else str(detail)
        raise PlaneError(
            f"Plane RPC failed ({message}); reconcile state before retrying a write",
            transient=bool(TRANSIENT.search(str(message))),
        )
    result = envelope["result"]
    if result.get("isError"):
        message = " ".join(
            str(part.get("text", "")) for part in result.get("content") or []
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip() or "unspecified error"
        raise PlaneError(
            f"Plane operation failed ({message}); reconcile state before retrying a write",
            transient=bool(TRANSIENT.search(message)),
        )
    return json.loads(next(c["text"] for c in result["content"] if c["type"] == "text"))


def probe(token, attempts=None, sleep=time.sleep):
    """One credential, judged with the same tolerance the real calls get."""
    total = attempts or (1 + AUTH_ATTEMPTS)
    for index in range(total):
        try:
            return _call_once("project", {"action": "list", "per_page": 1}, token)
        except PlaneError as error:
            if error.auth and index + 1 < total:
                sleep(AUTH_WAITS[min(index, len(AUTH_WAITS) - 1)])
                continue
            raise


def call(name, arguments, attempts=None, sleep=time.sleep):
    """One logical Plane call: survive throttling, then rotate a truly rejected credential.

    The hosted endpoint throttles with `429 Too Many Requests` and then answers
    `401 invalid_token` for a token that is still valid, so a single rejection proves
    nothing and stopping an agent to ask for a new key is wrong. A rejection is therefore
    retried on the same credential with backoff before another candidate is tried, and the
    credential that worked is reused for the rest of the process.
    """
    total = attempts or ATTEMPTS
    last, tried = None, []
    for source, token in credentials():
        transient_left, rejections_left = total, AUTH_ATTEMPTS
        while True:
            try:
                result = _call_once(name, arguments, token)
                CREDENTIAL.update(source=source, token=token)
                return result
            except PlaneError as error:
                last = error
                if error.auth:
                    if rejections_left <= 0:
                        tried.append(source)
                        break  # every attempt rejected this credential
                    rejections_left -= 1
                    sleep(error.retry_after or AUTH_WAITS[min(
                        AUTH_ATTEMPTS - rejections_left - 1, len(AUTH_WAITS) - 1)])
                    continue
                if not error.transient:
                    raise
                transient_left -= 1
                if transient_left <= 0:
                    raise
                sleep(error.retry_after or min(
                    1.0 * 2 ** (total - transient_left - 1), RETRY_CAP))
    throttled = "Too Many Requests" in str(last) or "429" in str(last)
    suffix = " (throttled: retry shortly)" if throttled else ""
    raise PlaneError(f"{last} (rejected credentials: {', '.join(tried) or 'none'}){suffix}",
                     auth=bool(last and last.auth))


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


def delivery_command(command, argv):
    """Delegate the delivery sweep; `prdev` is the dev-to-main request, never a merge."""
    import delivery  # local import keeps the Plane-only commands free of its cost

    if command == "prdev":
        argv = ["pr", *argv]
    elif not argv or argv[0] in {"-h", "--help"}:
        argv = ["scan", "--help"]
    return delivery.main(argv, plane_adapter())


def plane_adapter():
    """The narrow Plane surface the delivery sweep needs.

    Read paths reuse this module's retrying calls directly; the review boundary is
    delegated to the already-verified `review` command so there is exactly one
    implementation of the receipt/evidence rules.
    """

    class Adapter:
        pages = staticmethod(pages)
        unique = staticmethod(unique)
        states = staticmethod(states)
        context = staticmethod(context)

        @staticmethod
        def review_boundary(project_id, task_id, receipt, evidence):
            holder = Path(tempfile.mkdtemp(prefix="megai-boundary."))
            try:
                receipt_path = holder / "receipt.json"
                evidence_path = holder / "evidence.md"
                receipt_path.write_text(json.dumps(receipt))
                evidence_path.write_text(evidence)
                run = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "review",
                     "--project-id", project_id, "--task-id", task_id,
                     "--receipt", str(receipt_path),
                     "--evidence-file", str(evidence_path)],
                    capture_output=True, text=True, timeout=300,
                )
                if run.returncode:
                    detail = (run.stderr or run.stdout).strip() or f"exit {run.returncode}"
                    raise PlaneError(f"Plane review boundary failed: {detail}",
                                     transient=bool(TRANSIENT.search(detail)))
                return json.loads(run.stdout)
            finally:
                shutil.rmtree(holder, ignore_errors=True)

    return Adapter()


def plane_check(repair=False):
    """Probe every credential source; optionally install a working one as the canonical file.

    A rejected token must never be a dead end: usually a valid credential already exists
    somewhere else on the machine (an exported variable, the token file this machine's MCP
    server declares). Repair copies that proven token into the canonical file so every
    later session and the MCP proxy start healthy, and keeps the old file as a backup.
    """
    report = {"tokenFile": str(TOKEN_FILE), "candidates": [], "working": None, "repaired": None}
    working = None
    for source, token in tokens(TOKEN_FILE):
        entry = {"source": source, "canonical": source == "credential file"}
        try:
            probe(token)
            entry["status"] = "accepted"
            working = working or (source, token)
        except PlaneError as error:
            entry["status"] = "rejected" if error.auth else "unreachable"
            entry["detail"] = str(error)
        report["candidates"].append(entry)
    if working:
        report["working"] = working[0]
    canonical_ok = any(c["canonical"] and c["status"] == "accepted" for c in report["candidates"])
    if not repair:
        report["hint"] = ("credential accepted" if canonical_ok else
                          "run plane-check --repair to install the accepted credential"
                          if working else
                          f"no accepted credential; write a fresh token to {TOKEN_FILE}")
        return report
    if not working:
        report["hint"] = f"no accepted credential to install; write a fresh token to {TOKEN_FILE}"
        return report
    if canonical_ok:
        report["hint"] = "canonical credential already accepted"
        return report
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if TOKEN_FILE.exists():
        backup = TOKEN_FILE.with_name(TOKEN_FILE.name + ".backup")
        shutil.copy2(TOKEN_FILE, backup)
        os.chmod(backup, 0o600)
    handle = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(handle, (working[1] + "\n").encode())
    finally:
        os.close(handle)
    os.chmod(TOKEN_FILE, 0o600)
    CREDENTIAL.update(source="credential file", token=working[1])
    report["repaired"] = {"from": working[0], "tokenFile": str(TOKEN_FILE),
                          "backup": str(backup) if backup else None}
    report["hint"] = "canonical credential replaced from an accepted source"
    return report


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
    # /mdev and /prdev run their own multi-step sweep; their options are passed through
    # unchanged so the workflow CLI stays the single installed entry point.
    cmd = sub.add_parser("plane-check")
    cmd.add_argument("--repair", action="store_true")
    sub.add_parser("mdev")
    sub.add_parser("prdev")
    args, delivery_argv = parser.parse_known_args()
    if args.command in ("mdev", "prdev"):
        return delivery_command(args.command, delivery_argv)
    if delivery_argv:
        parser.error(f"unrecognized arguments: {' '.join(delivery_argv)}")
    if args.command == "plane-check":
        return plane_check(args.repair)
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
        print(json.dumps(main(), indent=2, default=str))
    except (
        ValueError,
        KeyError,
        OSError,
        StopIteration,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        sys.exit(1)
