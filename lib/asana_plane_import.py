#!/usr/bin/env python3
"""Private, resumable Asana snapshot -> Plane importer.

The importer deliberately has no Asana or Plane SDK dependency.  ``plan`` is
local-only; ``apply`` is the only command which writes to Plane.  A source
snapshot and its ledger must live outside a git checkout.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import ipaddress
import json
import mimetypes
import os
import re
import socket
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

API_ORIGIN = "https://api.plane.so"
EXTERNAL_SOURCE = "asana-migration-v1"
RATE_INTERVAL = 1.1
SIGNED_QUERY_KEYS = {"x-amz-algorithm", "x-amz-credential", "x-amz-date", "x-amz-expires", "x-amz-signature", "x-amz-security-token", "signature", "sig", "token", "expires"}
SECRET_KEY_RE = re.compile(r"(?:authorization|bearer|access[_-]?token|refresh[_-]?token|api[_-]?key|token|secret|password|presign|signature|x-amz-[^\s]+)", re.I)
SIGNED_URL_RE = re.compile(r"https?://[^\s'\"<>]*(?:x-amz-|x-goog-|signature=|sig=|token=|access_token=|expires=)[^\s'\"<>]*", re.I)
BEARER_RE = re.compile(r"\bBearer\s+[^\s,;]+", re.I)


class MigrationError(RuntimeError):
    """A safe, actionable migration failure."""


class AmbiguousWrite(MigrationError):
    pass


class ConflictError(MigrationError):
    pass


class _SafeHTML(HTMLParser):
    allowed = {"a", "b", "br", "code", "em", "i", "li", "ol", "p", "pre", "strong", "ul", "s", "del", "blockquote"}
    attrs = {"a": {"href", "title"}}
    drop = {"script", "style", "iframe", "object", "embed", "svg", "form", "input", "meta", "link"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.drop:
            self.depth += 1
            return
        if self.depth or tag not in self.allowed:
            return
        clean: list[str] = []
        for key, value in attrs:
            key = key.lower()
            if key not in self.attrs.get(tag, set()) or value is None:
                continue
            if key == "href":
                value = safe_http_url(value)
                if value is None:
                    continue
            clean.append(f' {key}="{html.escape(value, quote=True)}"')
        self.out.append(f"<{tag}{''.join(clean)}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.drop and self.depth:
            self.depth -= 1
        elif not self.depth and tag in self.allowed and tag != "br":
            self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.depth:
            self.out.append(html.escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.depth:
            self.out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.depth:
            self.out.append(f"&#{name};")


def safe_http_url(value: Any) -> str | None:
    """Return an http(s) URL without javascript/data/private-network targets."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urllib.parse.urlsplit(value.strip())
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        return None
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    if any(key.lower() in SIGNED_QUERY_KEYS or key.lower().startswith("x-amz-") for key, _ in query):
        return None
    if parsed.hostname.lower() in {"localhost", "localhost.localdomain"}:
        return None
    try:
        address = ipaddress.ip_address(parsed.hostname)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast:
            return None
    except ValueError:
        # DNS is not resolved for ordinary content URLs.  Network fetches use
        # safe_fetch_url, which resolves and checks every address.
        pass
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc, parsed.path, parsed.query, ""))


def sanitize_html(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    parser = _SafeHTML()
    parser.feed(value)
    parser.close()
    return "".join(parser.out)


def strip_ephemeral_urls(value: Any, *, _key: str = "") -> Any:
    """Make a user-facing provenance copy without bearer/presigned material."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            low = str(key).lower()
            if SECRET_KEY_RE.search(low) or low in {"token", "download_url", "upload_url", "presigned_url", "signed_url"}:
                continue
            result[key] = strip_ephemeral_urls(item, _key=low)
        return result
    if isinstance(value, list):
        return [strip_ephemeral_urls(item, _key=_key) for item in value]
    if isinstance(value, str) and ("url" in _key.lower() or value.startswith(("http://", "https://"))):
        url = safe_http_url(value)
        if not url:
            return None
        parsed = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        if any(k.lower() in SIGNED_QUERY_KEYS or k.lower().startswith("x-amz-") for k, _ in query):
            return None
        return url
    return value


def redact_secrets(value: Any) -> Any:
    """Deep-redact values for logs; never print token contents or credentials."""
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SECRET_KEY_RE.search(str(k)) else redact_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    if isinstance(value, str):
        value = BEARER_RE.sub("Bearer [REDACTED]", value)
        return SIGNED_URL_RE.sub("[REDACTED_URL]", value)
    return value


def read_token_file(path: str | os.PathLike[str]) -> str:
    file = Path(path)
    info = file.lstat()
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise MigrationError("token file must be a regular non-symlink file")
    if info.st_mode & 0o077 or info.st_uid != os.getuid():
        raise MigrationError("token file must be owned by the current user and mode 0600")
    token = file.read_text(encoding="utf-8").strip()
    if not token or "\n" in token or "\r" in token:
        raise MigrationError("token file is empty or malformed")
    return token


def source_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    path = (root / relative).resolve()
    if path != root and root not in path.parents:
        raise MigrationError("source path escapes private root")
    if path.exists() and path.is_symlink():
        raise MigrationError(f"symlink source path: {relative}")
    return path


def load_json(root: Path, relative: str, default: Any = None) -> Any:
    file = source_path(root, relative)
    if not file.exists():
        if default is not None:
            return default
        raise MigrationError(f"missing source record: {relative}")
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"invalid source record {relative}: {exc}") from exc


def records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict) and isinstance(value.get("data"), list):
        return [x for x in value["data"] if isinstance(x, dict)]
    if isinstance(value, dict) and isinstance(value.get("results"), list):
        return [x for x in value["results"] if isinstance(x, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def source_id(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise MigrationError("invalid source identity")
    return value


def section_name(section: Any) -> str:
    if isinstance(section, dict):
        return str(section.get("name") or section.get("section", {}).get("name") or "").strip()
    return str(section or "").strip()


def map_section_to_state(section: Any, completed: bool = False) -> dict[str, str]:
    """Map Asana sections to Plane semantic groups; completion always wins."""
    name = section_name(section)
    folded = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    if completed:
        group = "completed"
    elif re.search(r"\b(review|qa|quality|testing|test)\b", folded):
        group = "started"
    elif re.search(r"\b(progress|doing|active|started|develop)\b", folded):
        group = "started"
    elif re.search(r"\b(cancel|archive|rejected|declined)\b", folded):
        group = "cancelled"
    elif re.search(r"\b(backlog|later|icebox|inbox)\b", folded):
        group = "backlog"
    else:
        group = "unstarted"
    return {"name": name or group.title(), "group": group}


def task_memberships(task: dict[str, Any]) -> list[dict[str, Any]]:
    memberships = task.get("memberships")
    if not isinstance(memberships, list):
        return []
    return [m for m in memberships if isinstance(m, dict)]


def membership_project_ids(task: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for membership in task_memberships(task):
        project = membership.get("project")
        gid = project.get("gid") if isinstance(project, dict) else membership.get("project_gid")
        if gid is not None:
            sid = source_id(str(gid))
            if sid not in ids:
                ids.append(sid)
    return ids


def validate_memberships(tasks: Iterable[dict[str, Any]], selected_project: str | None = None) -> None:
    for task in tasks:
        ids = membership_project_ids(task)
        if len(ids) > 1:
            raise MigrationError(f"ambiguous multi-project task {task.get('gid')}: {','.join(ids)}")
        if selected_project and ids and ids[0] != selected_project:
            continue


def _task_parent(task: dict[str, Any]) -> str | None:
    parent = task.get("parent")
    if isinstance(parent, dict):
        return str(parent.get("gid")) if parent.get("gid") is not None else None
    return str(parent) if parent else None


def order_tasks(tasks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable parent-before-child order, with cycle detection."""
    by_id = {source_id(str(t.get("gid"))): t for t in tasks if t.get("gid") is not None}
    visiting: set[str] = set()
    done: set[str] = set()
    ordered: list[dict[str, Any]] = []

    def visit(gid: str) -> None:
        if gid in done:
            return
        if gid in visiting:
            raise MigrationError(f"subtask parent cycle at {gid}")
        visiting.add(gid)
        parent = _task_parent(by_id[gid])
        if parent in by_id:
            visit(parent)
        visiting.remove(gid)
        done.add(gid)
        ordered.append(by_id[gid])

    for gid in sorted(by_id):
        visit(gid)
    return ordered


def semantic_description(record: dict[str, Any]) -> tuple[str, str]:
    raw_html = record.get("html_notes") or record.get("description_html") or ""
    clean_html = sanitize_html(raw_html)
    plain = record.get("notes") or record.get("description_stripped") or ""
    if not isinstance(plain, str):
        plain = ""
    return clean_html, plain


def _hash_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


FINGERPRINT_FIELDS = {
    "projects": ("id", "external_source", "external_id", "name", "identifier", "description", "network", "archived"),
    "tasks": ("id", "external_source", "external_id", "name", "description", "description_html", "description_stripped", "state", "parent", "assignees", "labels", "start_date", "target_date", "completed_at", "archived_at"),
    "states": ("id", "external_source", "external_id", "name", "color", "group"),
    "labels": ("id", "external_source", "external_id", "name", "color", "description", "parent"),
    "comments": ("id", "external_source", "external_id", "comment_html", "comment_json", "access", "parent"),
    "attachments": ("id", "external_source", "external_id", "name", "size", "is_uploaded", "sha256", "bytes"),
}


def owned_fingerprint(kind: str, value: Any) -> str:
    """Hash only migration-owned content, not API activity/count timestamps."""
    fields = FINGERPRINT_FIELDS.get(kind)
    if fields is None or not isinstance(value, dict):
        return _hash_json(value)
    selected = {field: value.get(field) for field in fields if field in value}
    return _hash_json(selected)


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    temp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temp, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


class Ledger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = source_path(root, "destination-ledger.json")
        self.lock_path = source_path(root, "destination-ledger.lock")
        self.data = load_json(root, "destination-ledger.json", {"schema_version": 1, "pending": {}, "projects": {}, "tasks": {}, "states": {}, "labels": {}, "comments": {}, "attachments": {}})
        if not isinstance(self.data, dict):
            raise MigrationError("invalid destination ledger")
        self.fd: int | None = None

    def __enter__(self) -> "Ledger":
        try:
            self.fd = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.write(self.fd, f"pid={os.getpid()}\n".encode())
        except FileExistsError as exc:
            raise MigrationError("another migration writer holds the destination ledger lock") from exc
        return self

    def __exit__(self, *_: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass

    def save(self) -> None:
        atomic_json(self.path, redact_secrets(self.data))

    def check_pending(self, kind: str, key: str, payload: Any) -> None:
        existing = self.data.setdefault("pending", {}).get(f"{kind}:{key}")
        if existing and existing.get("payload_hash") != _hash_json(payload):
            raise MigrationError(f"pending {kind} receipt payload mismatch for {key}; refusing a different POST")

    def pending(self, kind: str, key: str, payload: Any) -> None:
        self.check_pending(kind, key, payload)
        self.data.setdefault("pending", {})[f"{kind}:{key}"] = {"payload_hash": _hash_json(payload), "kind": kind, "source_id": key, "created_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        self.save()

    def complete(self, kind: str, key: str, value: dict[str, Any]) -> None:
        self.data.setdefault("pending", {}).pop(f"{kind}:{key}", None)
        self.data.setdefault(kind, {})[key] = value
        self.save()

    def mapping(self, kind: str, key: str) -> dict[str, Any] | None:
        value = self.data.get(kind, {}).get(key)
        return value if isinstance(value, dict) else None

    def mark_detail_pending(self, source_gid: str, *, stories: int, attachments: int, gaps: list[dict[str, Any]] | None = None) -> None:
        pending = {"stories": stories, "attachments": attachments, "status": "pending", "gaps": gaps or []}
        self.data.setdefault("detail_pending", {})[source_gid] = pending
        if gaps:
            self.data.setdefault("fidelity_gaps", []).extend(gaps)
        self.save()

    def clear_detail_pending(self, source_gid: str) -> None:
        self.data.setdefault("detail_pending", {}).pop(source_gid, None)
        self.save()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        raise urllib.error.HTTPError(req.full_url, code, "redirect rejected", headers, fp)


class PlaneClient:
    def __init__(self, token: str, workspace_slug: str, *, opener: Any = None, sleep_fn: Any = time.sleep) -> None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{1,63}", workspace_slug):
            raise MigrationError("invalid destination workspace slug")
        self.token = token
        self.slug = workspace_slug
        self.opener = opener or urllib.request.build_opener(_NoRedirect())
        self.sleep_fn = sleep_fn
        self.next_at = 0.0

    def _url(self, path: str) -> str:
        if not path.startswith("/") or path.startswith("//"):
            raise MigrationError("invalid Plane API path")
        return API_ORIGIN + path

    def request(self, method: str, path: str, payload: Any = None, *, query: dict[str, str] | None = None, retry_get: bool = True) -> Any:
        if method not in {"GET", "POST", "PATCH"}:
            raise MigrationError("unsupported HTTP method")
        url = self._url(path)
        if query:
            url += "?" + urllib.parse.urlencode(query)
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
        headers = {"Accept": "application/json", "X-API-Key": self.token}
        if body is not None:
            headers["Content-Type"] = "application/json"
        attempts = 5 if method == "GET" and retry_get else 1
        for attempt in range(attempts):
            delay = max(0.0, self.next_at - time.monotonic())
            if delay:
                self.sleep_fn(delay)
            self.next_at = max(time.monotonic(), self.next_at) + RATE_INTERVAL
            request = urllib.request.Request(url, data=body, method=method, headers=headers)
            try:
                with self.opener.open(request, timeout=120) as response:
                    raw = response.read()
                    if not raw:
                        return None
                    try:
                        return json.loads(raw.decode("utf-8"))
                    except json.JSONDecodeError as exc:
                        raise MigrationError(f"Plane returned invalid JSON for {method} {path}") from exc
            except urllib.error.HTTPError as exc:
                exc.read()
                if method == "GET" and exc.code in {429, 502, 503, 504} and attempt + 1 < attempts:
                    retry = exc.headers.get("Retry-After") if exc.headers else None
                    try:
                        wait = max(0.0, min(120.0, float(retry))) if retry else 2 ** attempt
                    except ValueError:
                        wait = 2 ** attempt
                    self.sleep_fn(wait)
                    continue
                if method != "GET" and exc.code >= 500:
                    raise AmbiguousWrite(f"Plane {method} may have succeeded ({exc.code}); reconcile external identity before retry") from exc
                raise MigrationError(f"Plane {method} {path} failed ({exc.code})")
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if method == "GET" and attempt + 1 < attempts:
                    self.sleep_fn(2 ** attempt)
                    continue
                if method != "GET":
                    raise AmbiguousWrite(f"Plane {method} transport outcome is ambiguous; reconcile external identity before retry") from exc
                raise MigrationError(f"Plane GET failed: {type(exc).__name__}") from exc
        raise MigrationError(f"Plane GET failed after retries: {path}")

    def project(self, project_id: str) -> Any:
        return self.request("GET", f"/api/v1/workspaces/{self.slug}/projects/{project_id}/")

    def work_item(self, project_id: str, item_id: str) -> Any:
        return self.request("GET", f"/api/v1/workspaces/{self.slug}/projects/{project_id}/work-items/{item_id}/")

    def comment(self, project_id: str, item_id: str, comment_id: str) -> Any:
        return self.request("GET", f"/api/v1/workspaces/{self.slug}/projects/{project_id}/work-items/{item_id}/comments/{comment_id}/")

    def find_comment(self, project_id: str, item_id: str, external_id: str) -> Any | None:
        candidates = self.list_pages(f"/api/v1/workspaces/{self.slug}/projects/{project_id}/work-items/{item_id}/comments/", {"external_source": EXTERNAL_SOURCE, "external_id": external_id})
        for candidate in candidates:
            if candidate.get("external_source") == EXTERNAL_SOURCE and str(candidate.get("external_id")) == external_id:
                return candidate
        return None

    def list_pages(self, path: str, query: dict[str, str] | None = None) -> list[dict[str, Any]]:
        records_out: list[dict[str, Any]] = []
        current_path = path
        current_query = dict(query or {})
        seen: set[str] = set()
        for _ in range(1000):
            result = self.request("GET", current_path, query=current_query)
            records_out.extend(records(result))
            if not isinstance(result, dict):
                return records_out
            has_next = result.get("next_page_results")
            if has_next is False:
                return records_out
            marker = result.get("next_cursor") or result.get("next_page") or result.get("next")
            if has_next is True and not marker:
                raise MigrationError("Plane pagination declared next page without a cursor")
            if not marker:
                return records_out
            if isinstance(marker, dict):
                marker = marker.get("cursor") or marker.get("next_cursor") or marker.get("offset") or marker.get("url")
            if not isinstance(marker, str) or not marker:
                raise MigrationError("malformed Plane pagination cursor")
            if marker in seen:
                raise MigrationError("repeated Plane pagination cursor")
            seen.add(marker)
            if marker.startswith(API_ORIGIN + "/"):
                parsed = urllib.parse.urlsplit(marker)
                current_path = parsed.path
                current_query = dict(urllib.parse.parse_qsl(parsed.query))
            elif marker.startswith("/"):
                parsed = urllib.parse.urlsplit(API_ORIGIN + marker)
                current_path = parsed.path
                current_query = dict(urllib.parse.parse_qsl(parsed.query))
            else:
                current_query = {**current_query, "cursor": marker}
        raise MigrationError("Plane pagination exceeded safety limit")

    def find_external(self, resource: str, project_id: str | None, external_id: str) -> Any | None:
        if resource == "projects":
            path = f"/api/v1/workspaces/{self.slug}/projects/"
        elif resource == "work-items":
            if not project_id:
                raise MigrationError("work-item lookup requires project")
            path = f"/api/v1/workspaces/{self.slug}/projects/{project_id}/work-items/"
        elif resource == "states":
            path = f"/api/v1/workspaces/{self.slug}/projects/{project_id}/states/"
        elif resource == "labels":
            path = f"/api/v1/workspaces/{self.slug}/projects/{project_id}/labels/"
        else:
            raise MigrationError(f"unsupported reconciliation resource {resource}")
        candidates = self.list_pages(path, {"external_source": EXTERNAL_SOURCE, "external_id": external_id})
        for candidate in candidates:
            if candidate.get("external_source") == EXTERNAL_SOURCE and str(candidate.get("external_id")) == str(external_id):
                return candidate
        return None

    def download_checksum(self, target: str) -> str:
        checked = safe_storage_url(target)
        request = urllib.request.Request(checked, method="GET", headers={"Accept": "application/octet-stream"})
        digest = hashlib.sha256()
        try:
            with urllib.request.build_opener(_NoRedirect()).open(request, timeout=120) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
        except urllib.error.HTTPError as exc:
            raise MigrationError(f"credential-free destination attachment readback failed ({exc.code})") from exc
        except (urllib.error.URLError, OSError) as exc:
            raise MigrationError("credential-free destination attachment readback failed") from exc
        return digest.hexdigest()

    def upload_file(self, credentials: dict[str, Any], file: Path, content_type: str) -> None:
        target = credentials.get("url") or credentials.get("upload_url")
        if not isinstance(target, str):
            raise MigrationError("Plane upload response omitted storage URL")
        checked = safe_storage_url(target)
        fields = credentials.get("fields") or credentials.get("form_data") or credentials
        if not isinstance(fields, dict):
            raise MigrationError("Plane upload response omitted form fields")
        body, boundary = multipart(fields, file, content_type)
        request = urllib.request.Request(checked, data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))})
        try:
            with urllib.request.build_opener(_NoRedirect()).open(request, timeout=120) as response:
                if response.status not in {200, 201, 204}:
                    raise MigrationError(f"Plane storage upload failed ({response.status})")
        except urllib.error.HTTPError as exc:
            raise MigrationError(f"Plane storage upload failed ({exc.code})") from exc


def safe_storage_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise MigrationError("unsafe attachment storage URL")
    host = parsed.hostname.lower()
    if not (host.endswith(".amazonaws.com") or host.endswith(".digitaloceanspaces.com") or host == urllib.parse.urlsplit(API_ORIGIN).hostname):
        raise MigrationError("unapproved attachment storage host")
    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise MigrationError("could not validate attachment storage host") from exc
    if any(addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_multicast for addr in addresses):
        raise MigrationError("private attachment storage address rejected")
    return urllib.parse.urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, ""))


def multipart(fields: dict[str, Any], file: Path, content_type: str) -> tuple[bytes, str]:
    boundary = "----megai-plane-" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for key, value in fields.items():
        if key.lower() in {"file", "authorization", "token", "secret"} or not isinstance(value, (str, int, float)):
            continue
        chunks += [f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(), str(value).encode(), b"\r\n"]
    name = file.name.replace('"', "_")
    chunks += [f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'.encode(), f"Content-Type: {content_type}\r\n\r\n".encode(), file.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()]
    return b"".join(chunks), boundary


class Snapshot:
    def __init__(self, root: str | os.PathLike[str], source_workspace_gid: str) -> None:
        self.root = Path(root).resolve()
        if (self.root / ".git").exists():
            raise MigrationError("private export must be outside a git checkout")
        if not self.root.exists() or not self.root.is_dir() or (self.root.stat().st_mode & 0o077):
            raise MigrationError("private export directory must exist and be mode 0700")
        self.manifest = load_json(self.root, "source/manifest.json")
        if self.manifest.get("source_workspace_gid") != source_workspace_gid:
            raise MigrationError("approved source workspace does not match snapshot")
        if not self.manifest.get("export_complete"):
            raise MigrationError("source export is incomplete; apply is blocked")
        self.scope = self.manifest.get("scope", {"kind": "unspecified"})
        self.coverage_gaps = self.manifest.get("coverage_gaps", self.manifest.get("gaps", []))
        if not isinstance(self.coverage_gaps, list):
            raise MigrationError("source coverage_gaps must be a list")
        # Account-wide parity is an explicit exporter claim; export_complete
        # only proves the declared snapshot scope was read completely.
        self.full_account_export_complete = bool(self.manifest.get("full_account_export_complete", False))
        self.projects = {source_id(str(p["gid"])): p for p in self.manifest.get("projects", []) if isinstance(p, dict) and p.get("gid") is not None}
        self.tasks: dict[str, dict[str, Any]] = {}
        task_ids = self.manifest.get("tasks", [])
        for gid in task_ids:
            sid = source_id(str(gid))
            self.tasks[sid] = load_json(self.root, f"source/tasks/{sid}.json")
        self.my_tasks = [source_id(str(t.get("gid"))) for t in records(load_json(self.root, "source/my-tasks.json", [])) if t.get("gid") is not None]

    def project_detail(self, gid: str) -> dict[str, Any]:
        return load_json(self.root, f"source/projects/{source_id(gid)}.json")

    def task_stories(self, gid: str) -> list[dict[str, Any]]:
        return records(load_json(self.root, f"source/stories/{source_id(gid)}.json", []))

    def attachments(self, gid: str) -> list[dict[str, Any]]:
        return records(load_json(self.root, f"source/attachments/{source_id(gid)}.json", []))

    def task_project(self, task: dict[str, Any], selected: str | None = None) -> str | None:
        ids = membership_project_ids(task)
        if len(ids) > 1:
            if selected and selected not in ids:
                return "__ambiguous_unrelated__"
            raise MigrationError(f"ambiguous multi-project task {task.get('gid')}: {','.join(ids)}")
        if ids:
            return ids[0]
        parent = _task_parent(task)
        if parent and parent in self.tasks:
            return self.task_project(self.tasks[parent], selected)
        return None

    def tasks_for(self, selected: str | None) -> list[dict[str, Any]]:
        if selected and selected not in self.projects:
            raise MigrationError(f"unknown source project {selected}")
        selected_tasks = [t for t in self.tasks.values() if self.task_project(t, selected) == selected]
        if selected is None:
            selected_tasks = [t for t in self.tasks.values() if self.task_project(t, selected) is None]
        return order_tasks(selected_tasks)


def project_payload(detail: dict[str, Any], external_id: str, *, placeholder: bool) -> dict[str, Any]:
    if placeholder:
        return {"name": f"Migration placeholder {external_id}", "identifier": "AS" + hashlib.sha256(external_id.encode()).hexdigest()[:8].upper(), "external_source": EXTERNAL_SOURCE, "external_id": external_id}
    clean_html, plain = semantic_description(detail)
    return {"name": str(detail.get("name") or f"Asana {external_id}"), "description": clean_html or plain, "external_source": EXTERNAL_SOURCE, "external_id": external_id}


def placeholder_matches(current: dict[str, Any], placeholder: dict[str, Any]) -> bool:
    """Adopt only an exact migration placeholder, never a name collision."""
    return all(current.get(field) == expected for field, expected in placeholder.items())


def task_payload(task: dict[str, Any], state_id: str, parent_id: str | None, *, assignees: list[str] | None = None, labels: list[str] | None = None) -> dict[str, Any]:
    clean_html, plain = semantic_description(task)
    payload: dict[str, Any] = {"name": str(task.get("name") or f"Asana task {task.get('gid')}"), "description_html": clean_html, "description_stripped": plain, "state": state_id, "external_source": EXTERNAL_SOURCE, "external_id": str(task["gid"])}
    if parent_id:
        payload["parent"] = parent_id
    if assignees:
        payload["assignees"] = assignees
    if labels:
        payload["labels"] = labels
    if task.get("start_on"):
        payload["start_date"] = task["start_on"]
    if task.get("due_on"):
        payload["target_date"] = task["due_on"]
    if task.get("completed"):
        payload["completed_at"] = task.get("completed_at") or dt.datetime.now(dt.timezone.utc).isoformat()
    return payload


CANONICAL_STATE_NAMES = {"backlog": "Backlog", "unstarted": "Todo", "started": "In Progress", "completed": "Done", "cancelled": "Cancelled", "triage": "Triage"}


def canonical_state(section: Any, completed: bool) -> dict[str, str]:
    mapped = map_section_to_state(section, completed)
    return {"name": CANONICAL_STATE_NAMES.get(mapped["group"], mapped["name"]), "group": mapped["group"]}


def state_payload(section: Any, completed: bool, external_id: str) -> dict[str, Any]:
    mapped = canonical_state(section, completed)
    return {"name": mapped["name"], "color": "#64748b", "group": mapped["group"], "external_source": EXTERNAL_SOURCE, "external_id": external_id}


def _project_sections(detail: dict[str, Any]) -> list[dict[str, Any]]:
    sections = detail.get("sections")
    return [x for x in sections if isinstance(x, dict)] if isinstance(sections, list) else []


def _source_section(task: dict[str, Any], project_id: str) -> dict[str, Any]:
    for membership in task_memberships(task):
        project = membership.get("project")
        gid = project.get("gid") if isinstance(project, dict) else membership.get("project_gid")
        if str(gid) == project_id:
            section = membership.get("section")
            return section if isinstance(section, dict) else {"name": section or "Unstarted"}
    return {"name": "Unstarted"}


def _metadata_bundle(snapshot: Snapshot, task: dict[str, Any], project_id: str, gaps: list[dict[str, Any]]) -> dict[str, Any]:
    attachments = snapshot.attachments(str(task["gid"]))
    safe_attachments = []
    for attachment in attachments:
        item = strip_ephemeral_urls(attachment)
        if isinstance(item, dict):
            receipt = load_json(snapshot.root, f"source/file-receipts/{attachment.get('gid')}.json", {})
            for key in ("bytes", "sha256", "name", "content_type"):
                if key in receipt:
                    item.setdefault(key, receipt[key])
            item.pop("path", None)
            safe_attachments.append(item)
    return {"schema_version": 1, "source_system": "asana", "source_project_gid": project_id, "source_scope": strip_ephemeral_urls(snapshot.scope), "source_coverage_gaps": strip_ephemeral_urls(snapshot.coverage_gaps), "source_task": strip_ephemeral_urls(copy.deepcopy(task)), "source_stories": strip_ephemeral_urls(snapshot.task_stories(str(task["gid"]))), "source_attachments": safe_attachments, "fidelity_gaps": gaps}


def _validate_receipt(snapshot: Snapshot, attachment: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    gid = source_id(str(attachment.get("gid")))
    file = source_path(snapshot.root, f"source/files/{gid}.bin")
    receipt = load_json(snapshot.root, f"source/file-receipts/{gid}.json")
    if not file.is_file() or file.is_symlink():
        raise MigrationError(f"missing private source attachment {gid}")
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    if digest != receipt.get("sha256") or file.stat().st_size != receipt.get("bytes"):
        raise MigrationError(f"source attachment checksum mismatch {gid}")
    return file, receipt


def _verify_identity(record: Any, external_id: str, source: str = EXTERNAL_SOURCE) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("external_source") != source or str(record.get("external_id")) != external_id:
        raise MigrationError("Plane readback did not prove migration ownership")
    return record


def _verify_owned_payload(kind: str, payload: dict[str, Any], current: dict[str, Any]) -> None:
    for field in FINGERPRINT_FIELDS.get(kind, ()):
        if field not in payload:
            continue
        if field not in current:
            raise MigrationError(f"Plane readback omitted submitted {kind} field {field}")
        expected = payload[field]
        actual = current[field]
        if isinstance(expected, dict):
            expected = expected.get("id") or expected
        if isinstance(actual, dict):
            actual = actual.get("id") or actual
        if isinstance(expected, list) and isinstance(actual, list):
            expected = [item.get("id") if isinstance(item, dict) else item for item in expected]
            actual = [item.get("id") if isinstance(item, dict) else item for item in actual]
        if expected != actual:
            raise MigrationError(f"Plane readback mismatch for {kind} field {field}")


def find_destination_attachment(value: Any, external_id: str) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if value.get("external_source") == EXTERNAL_SOURCE and str(value.get("external_id")) == external_id:
            return value
        for child in value.values():
            found = find_destination_attachment(child, external_id)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_destination_attachment(child, external_id)
            if found:
                return found
    return None


def destination_download_url(attachment: dict[str, Any]) -> str | None:
    for key in ("download_url", "url", "asset_url", "file_url"):
        value = attachment.get(key)
        if isinstance(value, str):
            try:
                return safe_storage_url(value)
            except MigrationError:
                continue
    return None


class Importer:
    def __init__(self, snapshot: Snapshot, client: PlaneClient, ledger: Ledger) -> None:
        self.snapshot = snapshot
        self.client = client
        self.ledger = ledger
        self.members: dict[str, str] | None = None
        self.state_cache: dict[str, dict[str, Any]] = {}
        self.state_meta: dict[str, tuple[str, str, str]] = {}
        self.label_cache: dict[str, dict[str, Any]] = {}

    def begin_project(self) -> None:
        self.state_cache.clear()
        self.state_meta.clear()
        self.label_cache.clear()

    def _migration_project(self, project_id: str) -> bool:
        return any(str(record.get("id")) == str(project_id) and record.get("external_id") and record.get("id") for record in self.ledger.data.get("projects", {}).values() if isinstance(record, dict))

    def _state_project_matches(self, record: dict[str, Any], project_id: str) -> bool:
        nested = record.get("project")
        candidate = nested.get("id") if isinstance(nested, dict) else nested
        candidate = record.get("project_id", candidate)
        return candidate is None or str(candidate) == str(project_id)

    def _verify_state(self, record: dict[str, Any], project_id: str, name: str, group: str) -> None:
        if record.get("name") != name or record.get("group") != group or not self._state_project_matches(record, project_id):
            raise MigrationError("Plane state readback did not prove exact project/name/group ownership")

    def verify_cached_definitions(self, project_id: str) -> None:
        for key, cached in self.state_cache.items():
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/states/{cached['id']}/")
            name, group, origin = self.state_meta[key]
            if origin == "created":
                _verify_identity(current, cached["external_id"])
            self._verify_state(current, project_id, name, group)
            if owned_fingerprint("states", current) != owned_fingerprint("states", cached):
                raise ConflictError(f"destination state drift detected for {key}")
        for key, cached in self.label_cache.items():
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/labels/{cached['id']}/")
            _verify_identity(current, cached["external_id"])
            if owned_fingerprint("labels", current) != owned_fingerprint("labels", cached):
                raise ConflictError(f"destination label drift detected for {key}")

    def _ensure(self, kind: str, key: str, collection: str, project_id: str | None, payload: dict[str, Any], create_path: str, readback: Any) -> dict[str, Any]:
        self.ledger.check_pending(kind, key, payload)
        old = self.ledger.mapping(kind, key)
        if old and old.get("id"):
            current = readback(str(old["id"]))
            _verify_identity(current, str(payload["external_id"]))
            _verify_owned_payload(kind, payload, current)
            old_hash = old.get("readback_hash")
            current_hash = owned_fingerprint(kind, current)
            if old_hash and old.get("fingerprint_version") == 1 and old_hash != current_hash:
                raise ConflictError(f"destination drift detected for {kind} {key}; refusing overwrite")
            if old.get("fingerprint_version") != 1:
                old["readback_hash"] = current_hash
                old["fingerprint_version"] = 1
                self.ledger.save()
            return current
        found = self.client.find_external(collection, project_id, str(payload["external_id"]))
        if found:
            current = readback(str(found["id"]))
            _verify_identity(current, str(payload["external_id"]))
            _verify_owned_payload(kind, payload, current)
            self.ledger.complete(kind, key, {"id": current.get("id"), "project_id": project_id, "readback_hash": owned_fingerprint(kind, current), "fingerprint_version": 1, "external_id": payload["external_id"]})
            return current
        self.ledger.pending(kind, key, payload)
        try:
            created = self.client.request("POST", create_path, payload)
        except AmbiguousWrite:
            found = self.client.find_external(collection, project_id, str(payload["external_id"]))
            if not found:
                raise
            created = found
        current = readback(str(created.get("id"))) if isinstance(created, dict) and created.get("id") else created
        _verify_identity(current, str(payload["external_id"]))
        _verify_owned_payload(kind, payload, current)
        self.ledger.complete(kind, key, {"id": current.get("id"), "project_id": project_id, "source_project_gid": project_id, "readback_hash": owned_fingerprint(kind, current), "fingerprint_version": 1, "external_id": payload["external_id"]})
        return current

    def ensure_project(self, source_gid: str, detail: dict[str, Any]) -> dict[str, Any]:
        placeholder = project_payload(detail, source_gid, placeholder=True)
        self.ledger.check_pending("projects", source_gid, placeholder)
        old = self.ledger.mapping("projects", source_gid)
        if old and old.get("id"):
            current = self.client.project(str(old["id"]))
            _verify_identity(current, source_gid)
            if current.get("network") != 0:
                raise MigrationError(f"resumed project {source_gid} is not private; no source data will be sent")
            current_hash = owned_fingerprint("projects", current)
            if old.get("fingerprint_version") == 1 and old.get("readback_hash") != current_hash:
                raise ConflictError(f"destination drift detected for project {source_gid}")
            if old.get("fingerprint_version") != 1:
                old["readback_hash"] = current_hash
                old["fingerprint_version"] = 1
                self.ledger.save()
            return current

        self.ledger.pending("projects", source_gid, placeholder)
        existing = self.client.find_external("projects", None, source_gid)
        if existing:
            current = self.client.project(str(existing["id"]))
            _verify_identity(current, source_gid)
            if not placeholder_matches(current, placeholder):
                raise MigrationError(f"migration-owned project {source_gid} is not the exact nonsensitive placeholder; refusing adoption")
        else:
            try:
                current = self.client.request("POST", f"/api/v1/workspaces/{self.client.slug}/projects/", placeholder)
            except AmbiguousWrite:
                current = self.client.find_external("projects", None, source_gid)
                if not current:
                    raise
            if not isinstance(current, dict) or not current.get("id"):
                raise MigrationError("Plane project create response omitted id")
            current = self.client.project(str(current["id"]))
            if not placeholder_matches(current, placeholder):
                raise MigrationError(f"Plane project {source_gid} did not preserve the exact nonsensitive placeholder")

        # The serializer does not accept network on create.  Set it with a
        # source-free PATCH, then read it back before any source title/content.
        self.client.request("PATCH", f"/api/v1/workspaces/{self.client.slug}/projects/{current['id']}/", {"network": 0})
        current = self.client.project(str(current["id"]))
        if current.get("network") != 0:
            raise MigrationError(f"Plane private-project verification failed for {source_gid}: network={current.get('network')!r}; no source data will be sent")

        patch = project_payload(detail, source_gid, placeholder=False)
        current = self.client.request("PATCH", f"/api/v1/workspaces/{self.client.slug}/projects/{current['id']}/", patch)
        current = self.client.project(str(current["id"]))
        _verify_identity(current, source_gid)
        _verify_owned_payload("projects", patch, current)
        if current.get("network") != 0:
            raise MigrationError(f"Plane changed project privacy during source patch for {source_gid}")
        self.ledger.complete("projects", source_gid, {"id": current["id"], "readback_hash": owned_fingerprint("projects", current), "fingerprint_version": 1, "external_id": source_gid})
        return current

    def ensure_state(self, project_id: str, section: dict[str, Any], completed: bool) -> dict[str, Any]:
        mapped = canonical_state(section, completed)
        source_section_id = str(section.get("gid") or _hash_json(section)[:16])
        key = f"{project_id}:{mapped['group']}"
        payload = state_payload(section, completed, key)
        self.ledger.check_pending("states", key, payload)
        if key in self.state_cache:
            state_record = self.ledger.mapping("states", key)
            if state_record and source_section_id not in state_record.setdefault("source_section_ids", []):
                state_record["source_section_ids"].append(source_section_id)
                self.ledger.save()
            return self.state_cache[key]
        old = self.ledger.mapping("states", key)
        if old:
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/states/{old['id']}/")
            if old.get("origin") == "created":
                _verify_identity(current, key)
            self._verify_state(current, project_id, mapped["name"], mapped["group"])
            current_hash = owned_fingerprint("states", current)
            if old.get("fingerprint_version") == 1 and old.get("readback_hash") != current_hash:
                raise ConflictError(f"destination state drift detected for {key}")
            old["readback_hash"] = current_hash
            old["fingerprint_version"] = 1
            old.setdefault("source_section_ids", []).append(source_section_id)
            old["source_section_ids"] = sorted(set(old["source_section_ids"]))
            self.ledger.save()
            self.state_cache[key] = current
            self.state_meta[key] = (mapped["name"], mapped["group"], old.get("origin", "created"))
            return current

        found = self.client.find_external("states", project_id, key)
        origin = "created"
        if found:
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/states/{found['id']}/")
            _verify_identity(current, key)
        else:
            # Default Plane states have no external identity.  They may only be
            # reused after this project has passed our migration ownership gate.
            path = f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/states/"
            if self._migration_project(project_id):
                for candidate in self.client.list_pages(path):
                    if candidate.get("name") != mapped["name"] or candidate.get("group") != mapped["group"] or not self._state_project_matches(candidate, project_id):
                        continue
                    current = self.client.request("GET", f"{path}{candidate['id']}/")
                    self._verify_state(current, project_id, mapped["name"], mapped["group"])
                    origin = "reused_default"
                    break
                else:
                    current = None
            else:
                current = None
            if current is None:
                self.ledger.pending("states", key, payload)
                try:
                    current = self.client.request("POST", path, payload)
                except AmbiguousWrite:
                    current = self.client.find_external("states", project_id, key)
                    if not current:
                        raise
                if not isinstance(current, dict) or not current.get("id"):
                    raise MigrationError(f"state create response omitted id {key}")
                current = self.client.request("GET", f"{path}{current['id']}/")
        self._verify_state(current, project_id, mapped["name"], mapped["group"])
        if origin == "created":
            _verify_owned_payload("states", payload, current)
        self.ledger.complete("states", key, {"id": current["id"], "project_id": project_id, "origin": origin, "source_section_ids": [source_section_id], "readback_hash": owned_fingerprint("states", current), "fingerprint_version": 1, "external_id": key})
        self.state_cache[key] = current
        self.state_meta[key] = (mapped["name"], mapped["group"], origin)
        return current

    def _member_ids(self) -> dict[str, str]:
        if self.members is not None:
            return self.members
        result = self.client.list_pages(f"/api/v1/workspaces/{self.client.slug}/members/")
        self.members = {}
        for member in result:
            email = member.get("email") or member.get("member", {}).get("email") if isinstance(member.get("member"), dict) else member.get("email")
            member_id = member.get("id") or member.get("member_id") or member.get("member", {}).get("id") if isinstance(member.get("member"), dict) else member.get("id")
            if email and member_id:
                self.members[str(email).lower()] = str(member_id)
        return self.members

    def _assignee(self, task: dict[str, Any], gaps: list[dict[str, Any]]) -> list[str]:
        assignee = task.get("assignee")
        if not isinstance(assignee, dict) or not assignee.get("email"):
            return []
        email = str(assignee["email"]).lower()
        member = self._member_ids().get(email)
        if not member:
            gaps.append({"kind": "unmatched_assignee", "email": email, "source_gid": task.get("gid")})
            return []
        return [member]

    def ensure_label(self, project_id: str, tag: dict[str, Any]) -> str:
        tag_id = str(tag.get("gid") or _hash_json(tag)[:16])
        key = f"{project_id}:{tag_id}"
        payload = {"name": str(tag.get("name") or tag_id), "color": "#64748b", "external_source": EXTERNAL_SOURCE, "external_id": key}
        self.ledger.check_pending("labels", key, payload)
        if key in self.label_cache:
            return str(self.label_cache[key]["id"])
        old = self.ledger.mapping("labels", key)
        if old:
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/labels/{old['id']}/")
            _verify_identity(current, key)
            current_hash = owned_fingerprint("labels", current)
            if old.get("fingerprint_version") == 1 and old.get("readback_hash") != current_hash:
                raise ConflictError(f"destination label drift detected for {key}")
            _verify_owned_payload("labels", payload, current)
            old["readback_hash"] = current_hash
            old["fingerprint_version"] = 1
            self.ledger.save()
            self.label_cache[key] = current
            return str(current["id"])
        found = self.client.find_external("labels", project_id, key)
        if found:
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/labels/{found['id']}/")
        else:
            self.ledger.pending("labels", key, payload)
            try:
                current = self.client.request("POST", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/labels/", payload)
            except AmbiguousWrite:
                current = self.client.find_external("labels", project_id, key)
                if not current:
                    raise
            if not isinstance(current, dict) or not current.get("id"):
                raise MigrationError(f"label create response omitted id {key}")
            current = self.client.request("GET", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/labels/{current['id']}/")
        _verify_identity(current, key)
        _verify_owned_payload("labels", payload, current)
        self.ledger.complete("labels", key, {"id": current["id"], "project_id": project_id, "readback_hash": owned_fingerprint("labels", current), "fingerprint_version": 1, "external_id": key})
        self.label_cache[key] = current
        return str(current["id"])

    def import_task(self, project_source_gid: str, destination_project_id: str, task: dict[str, Any], task_map: dict[str, str], *, phase: str = "all") -> None:
        gid = source_id(str(task["gid"]))
        gaps: list[dict[str, Any]] = []
        state = self.ensure_state(destination_project_id, _source_section(task, project_source_gid), bool(task.get("completed")))
        parent_source = _task_parent(task)
        parent_destination = task_map.get(parent_source) if parent_source else None
        if parent_source and not parent_destination:
            raise MigrationError(f"parent {parent_source} has not been imported before child {gid}")
        labels = [self.ensure_label(destination_project_id, tag) for tag in task.get("tags", []) if isinstance(tag, dict)]
        payload = task_payload(task, str(state["id"]), parent_destination, assignees=self._assignee(task, gaps), labels=labels)
        current = self._ensure("tasks", gid, "work-items", destination_project_id, payload, f"/api/v1/workspaces/{self.client.slug}/projects/{destination_project_id}/work-items/", lambda item_id: self.client.work_item(destination_project_id, item_id))
        task_map[gid] = str(current["id"])
        task_record = self.ledger.mapping("tasks", gid)
        if task_record is not None:
            task_record["source_project_gid"] = project_source_gid
            self.ledger.save()
        stories = self.snapshot.task_stories(gid)
        attachments = self.snapshot.attachments(gid)
        if phase == "tasks":
            self.ledger.mark_detail_pending(gid, stories=len(stories), attachments=len(attachments), gaps=gaps)
            return
        # Native comments are best effort only for actual user comments.  The
        # bundle below remains authoritative for histories Plane cannot model.
        for story in stories:
            if story.get("resource_subtype") != "comment_added":
                gaps.append({"kind": "unsupported_story", "story_gid": story.get("gid")})
                continue
            story_id = str(story.get("gid"))
            comment_payload = {"comment_html": f"<p><strong>Original Asana comment by {html.escape(str(story.get('created_by', {}).get('name') if isinstance(story.get('created_by'), dict) else 'unknown'))} at {html.escape(str(story.get('created_at') or 'unknown'))}</strong></p><p>{sanitize_html(story.get('html_text') or story.get('text') or '')}</p>", "external_source": EXTERNAL_SOURCE, "external_id": story_id}
            old_comment = self.ledger.mapping("comments", story_id)
            if old_comment:
                readback = self.client.comment(destination_project_id, str(current["id"]), str(old_comment["id"]))
                _verify_identity(readback, story_id)
                _verify_owned_payload("comments", comment_payload, readback)
                if old_comment.get("fingerprint_version") == 1 and old_comment.get("readback_hash") != owned_fingerprint("comments", readback):
                    raise ConflictError(f"destination comment drift detected for {story_id}")
            else:
                self.ledger.pending("comments", story_id, comment_payload)
                try:
                    created = self.client.request("POST", f"/api/v1/workspaces/{self.client.slug}/projects/{destination_project_id}/work-items/{current['id']}/comments/", comment_payload)
                except AmbiguousWrite:
                    created = self.client.find_comment(destination_project_id, str(current["id"]), story_id)
                    if not created:
                        raise
                if not isinstance(created, dict) or not created.get("id"):
                    raise MigrationError(f"comment readback missing id {story_id}")
                readback = self.client.comment(destination_project_id, str(current["id"]), str(created["id"]))
                _verify_identity(readback, story_id)
                self.ledger.complete("comments", story_id, {"id": created["id"], "project_id": destination_project_id, "item_id": current["id"], "readback_hash": owned_fingerprint("comments", readback), "fingerprint_version": 1, "external_id": story_id})
        for attachment in attachments:
            self.import_attachment(destination_project_id, str(current["id"]), attachment)
        bundle = _metadata_bundle(self.snapshot, task, project_source_gid, gaps)
        self.import_bundle(destination_project_id, str(current["id"]), gid, bundle)
        self.ledger.clear_detail_pending(gid)
        self.ledger.save()

    def _verify_attachment_resume(self, project_id: str, task_id: str, source_gid: str, digest: str) -> None:
        old = self.ledger.mapping("attachments", source_gid)
        item = self.client.work_item(project_id, task_id)
        destination = find_destination_attachment(item, source_gid)
        if not destination or str(destination.get("id")) != str(old.get("id")):
            raise MigrationError(f"destination attachment readback missing or mismatched {source_gid}")
        _verify_identity(destination, source_gid)
        if old.get("sha256") != digest:
            raise ConflictError(f"source attachment checksum drift detected for {source_gid}")
        if old.get("fingerprint_version") == 1 and old.get("readback_hash") != owned_fingerprint("attachments", destination):
            raise ConflictError(f"destination attachment drift detected for {source_gid}")
        target = destination_download_url(destination)
        if not target or self.client.download_checksum(target) != digest:
            raise MigrationError(f"destination attachment checksum verification failed {source_gid}")

    def import_attachment(self, project_id: str, task_id: str, attachment: dict[str, Any]) -> None:
        source_gid = source_id(str(attachment.get("gid")))
        file, receipt = _validate_receipt(self.snapshot, attachment)
        old = self.ledger.mapping("attachments", source_gid)
        if old:
            self._verify_attachment_resume(project_id, task_id, source_gid, receipt["sha256"])
            return
        name = str(receipt.get("name") or attachment.get("name") or f"attachment-{source_gid}")
        content_type = str(receipt.get("content_type") or mimetypes.guess_type(name)[0] or "application/octet-stream")
        payload = {"name": name, "type": content_type, "size": int(receipt["bytes"]), "external_source": EXTERNAL_SOURCE, "external_id": source_gid}
        self.ledger.pending("attachments", source_gid, payload)
        credentials = self.client.request("POST", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/work-items/{task_id}/attachments/", payload)
        if not isinstance(credentials, dict):
            raise MigrationError(f"attachment credentials missing for {source_gid}")
        self.client.upload_file(credentials, file, content_type)
        resource_id = credentials.get("id") or credentials.get("resource_id") or credentials.get("attachment", {}).get("id")
        if not resource_id:
            raise MigrationError(f"attachment upload response omitted resource id {source_gid}")
        self.client.request("PATCH", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/work-items/{task_id}/attachments/{resource_id}/", {"is_uploaded": True})
        # Readback endpoint is not consistently documented; the work-item read
        # proves the parent write and lets verify() compare bytes where a safe
        # credential-free URL is exposed.
        item = self.client.work_item(project_id, task_id)
        destination = find_destination_attachment(item, source_gid)
        if not destination:
            raise MigrationError(f"destination attachment readback omitted external identity {source_gid}")
        target = destination_download_url(destination)
        if not target:
            raise MigrationError(f"destination attachment readback omitted a safe credential-free URL {source_gid}")
        if self.client.download_checksum(target) != receipt["sha256"]:
            raise MigrationError(f"destination attachment checksum mismatch {source_gid}")
        self.ledger.complete("attachments", source_gid, {"id": resource_id, "readback_hash": owned_fingerprint("attachments", destination), "fingerprint_version": 1, "external_id": source_gid, "sha256": receipt["sha256"], "bytes": receipt["bytes"]})

    def import_bundle(self, project_id: str, task_id: str, source_gid: str, bundle: dict[str, Any]) -> None:
        # The JSON bundle is generated privately and uploaded through the same
        # protected Plane attachment flow.  Its contents omit signed URLs.
        directory = Path(tempfile.mkdtemp(prefix="asana-plane-bundle-"))
        try:
            file = directory / "migration-record.json"
            file.write_text(json.dumps(bundle, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
            os.chmod(file, 0o600)
            digest = hashlib.sha256(file.read_bytes()).hexdigest()
            self.import_attachment_file(project_id, task_id, source_gid + ":migration-record", file, "application/json", digest)
        finally:
            try:
                file.unlink()
            except (UnboundLocalError, FileNotFoundError):
                pass
            directory.rmdir()

    def import_attachment_file(self, project_id: str, task_id: str, source_gid: str, file: Path, content_type: str, digest: str) -> None:
        if self.ledger.mapping("attachments", source_gid):
            self._verify_attachment_resume(project_id, task_id, source_gid, digest)
            return
        payload = {"name": "migration-record.json", "type": content_type, "size": file.stat().st_size, "external_source": EXTERNAL_SOURCE, "external_id": source_gid}
        self.ledger.pending("attachments", source_gid, payload)
        credentials = self.client.request("POST", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/work-items/{task_id}/attachments/", payload)
        self.client.upload_file(credentials, file, content_type)
        resource_id = credentials.get("id") or credentials.get("resource_id") or credentials.get("attachment", {}).get("id")
        if not resource_id:
            raise MigrationError(f"migration-record upload omitted resource id {source_gid}")
        self.client.request("PATCH", f"/api/v1/workspaces/{self.client.slug}/projects/{project_id}/work-items/{task_id}/attachments/{resource_id}/", {"is_uploaded": True})
        item = self.client.work_item(project_id, task_id)
        destination = find_destination_attachment(item, source_gid)
        if not destination:
            raise MigrationError(f"destination migration-record readback omitted external identity {source_gid}")
        target = destination_download_url(destination)
        if not target:
            raise MigrationError(f"destination migration-record readback omitted a safe credential-free URL {source_gid}")
        if self.client.download_checksum(target) != digest:
            raise MigrationError(f"destination migration-record checksum mismatch {source_gid}")
        self.ledger.complete("attachments", source_gid, {"id": resource_id, "readback_hash": owned_fingerprint("attachments", destination), "fingerprint_version": 1, "external_id": source_gid, "sha256": digest, "bytes": file.stat().st_size})

    def import_project(self, source_gid: str, *, phase: str = "all") -> dict[str, Any]:
        detail = self.snapshot.project_detail(source_gid)
        project = self.ensure_project(source_gid, detail)
        destination_id = str(project["id"])
        self.begin_project()
        task_map: dict[str, str] = {}
        for task in self.snapshot.tasks_for(source_gid):
            self.import_task(source_gid, destination_id, task, task_map, phase=phase)
        self.verify_cached_definitions(destination_id)
        if phase == "tasks":
            return {"source_gid": source_gid, "destination_id": destination_id, "tasks": len(task_map), "phase": "tasks", "full_verification": False, "archived": False, "details_pending": len(self.ledger.data.get("detail_pending", {})), "fidelity_gaps": self.ledger.data.get("fidelity_gaps", [])}
        if detail.get("archived"):
            # Archive only after child tasks, comments, uploads and bundles.
            self.client.request("POST", f"/api/v1/workspaces/{self.client.slug}/projects/{destination_id}/archive/")
            archived = self.client.project(destination_id)
            if not archived.get("archived_at") and not archived.get("archived"):
                raise MigrationError(f"project archive readback failed for {source_gid}")
        return {"source_gid": source_gid, "destination_id": destination_id, "tasks": len(task_map), "phase": "all", "full_verification": False, "verification_scope": "import_readbacks_only", "archived": bool(detail.get("archived")), "details_pending": len(self.ledger.data.get("detail_pending", {}))}

    def import_my_tasks(self, *, phase: str = "all") -> dict[str, Any]:
        # My Tasks is private and deliberately separate from source projects.
        detail = {"name": "Asana My Tasks (private import)", "notes": "Unprojected Asana tasks preserved by migration."}
        pseudo = "my-tasks"
        project = self.ensure_project(pseudo, {**detail, "gid": pseudo})
        self.begin_project()
        task_map: dict[str, str] = {}
        for task in self.snapshot.tasks_for(None):
            self.import_task(pseudo, str(project["id"]), task, task_map, phase=phase)
        self.verify_cached_definitions(str(project["id"]))
        return {"source_gid": pseudo, "destination_id": project["id"], "tasks": len(task_map), "private": True, "phase": phase, "full_verification": False, "verification_scope": "import_readbacks_only", "details_pending": len(self.ledger.data.get("detail_pending", {})), "fidelity_gaps": self.ledger.data.get("fidelity_gaps", [])}

    def verify(self, selected: str | None = None, *, phase: str = "all") -> dict[str, Any]:
        # Identity readbacks are not preservation proof. Until complete source
        # coverage and every detail are independently checked, fail closed even
        # for an empty pending queue or a complete source manifest.
        checked = 0
        for source_gid, mapping in self.ledger.data.get("projects", {}).items():
            if source_gid == "my-tasks" or selected is None or source_gid == selected:
                project = self.client.project(str(mapping["id"]))
                _verify_identity(project, source_gid)
                if project.get("network") != 0:
                    raise MigrationError(f"project {source_gid} is not private")
                checked += 1
        for source_gid, mapping in self.ledger.data.get("tasks", {}).items():
            if selected and mapping.get("source_project_gid") not in {selected, None}:
                continue
            if mapping.get("id") and mapping.get("project_id"):
                current = self.client.work_item(str(mapping["project_id"]), str(mapping["id"]))
                _verify_identity(current, source_gid)
                checked += 1
        return {"checked": checked, "pending": len(self.ledger.data.get("pending", {})), "details_pending": len(self.ledger.data.get("detail_pending", {})), "status": "partial", "phase": phase, "full_verification": False, "verification_scope": "core_identity_only", "unverified": ["complete source/destination coverage", "definitions", "comments", "attachments/checksums"], "source_scope": self.snapshot.scope, "coverage_gaps": self.snapshot.coverage_gaps, "full_account_export_complete": self.snapshot.full_account_export_complete}


def plan(snapshot: Snapshot, selected: str | None, all_projects: bool, *, phase: str = "all") -> dict[str, Any]:
    if selected and all_projects:
        raise MigrationError("choose --project or --all, not both")
    if not selected and not all_projects:
        raise MigrationError("apply requires --project SOURCE_GID or --all")
    projects = [selected] if selected else sorted(snapshot.projects)
    result = {"source_workspace_gid": snapshot.manifest["source_workspace_gid"], "projects": [], "my_tasks": False, "phase": phase, "export_complete": bool(snapshot.manifest.get("export_complete")), "source_scope": snapshot.scope, "coverage_gaps": snapshot.coverage_gaps, "full_account_export_complete": snapshot.full_account_export_complete, "full_account_parity": False}
    for project in projects:
        tasks = snapshot.tasks_for(project)
        result["projects"].append({"source_gid": project, "tasks": len(tasks), "archived": bool(snapshot.projects[project].get("archived"))})
    if all_projects:
        my_tasks = snapshot.tasks_for(None)
        result["my_tasks"] = bool(my_tasks)
        result["my_tasks_count"] = len(my_tasks)
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "apply", "resume", "verify"])
    parser.add_argument("--source", required=True, help="private export root (never a git checkout)")
    parser.add_argument("--source-workspace-gid", required=True)
    parser.add_argument("--workspace-slug", required=True)
    parser.add_argument("--token-file", help="owned mode-0600 token file; required for network commands")
    parser.add_argument("--phase", choices=["tasks", "all"], default="all", help="tasks imports core records only; all also imports details")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--project", help="one source project gid")
    scope.add_argument("--all", action="store_true", help="all projects plus unprojected My Tasks")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    snapshot = Snapshot(args.source, args.source_workspace_gid)
    selected = args.project
    if args.command == "plan":
        result = plan(snapshot, selected, args.all, phase=args.phase)
    else:
        if not args.token_file:
            raise MigrationError("--token-file is required for apply, resume and verify")
        token = read_token_file(args.token_file)
        client = PlaneClient(token, args.workspace_slug)
        with Ledger(snapshot.root) as ledger:
            importer = Importer(snapshot, client, ledger)
            if args.command in {"apply", "resume"}:
                if not selected and not args.all:
                    raise MigrationError("apply requires --project SOURCE_GID or --all")
                results = []
                for project_gid in ([selected] if selected else sorted(snapshot.projects)):
                    results.append(importer.import_project(project_gid, phase=args.phase))
                if args.all and snapshot.tasks_for(None):
                    results.append(importer.import_my_tasks(phase=args.phase))
                result = {"status": "applied", "results": results, "phase": args.phase, "pending": len(ledger.data.get("pending", {})), "details_pending": len(ledger.data.get("detail_pending", {})), "fidelity_gaps": ledger.data.get("fidelity_gaps", []), "full_verification": False, "verification_scope": "import_readbacks_only", "source_scope": snapshot.scope, "coverage_gaps": snapshot.coverage_gaps, "full_account_export_complete": snapshot.full_account_export_complete}
            else:
                result = importer.verify(selected, phase=args.phase)
    print(json.dumps(redact_secrets(result), sort_keys=True))
    return 2 if args.command == "verify" and result["status"] != "verified" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MigrationError as exc:
        print(f"migration blocked: {exc}", file=sys.stderr)
        raise SystemExit(2)
