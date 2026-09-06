import json
import sys
import urllib.parse
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "lib"))
import asana_plane_import as importer  # noqa: E402


def test_state_mapping_completed_overrides_review():
    assert importer.map_section_to_state({"name": "In Review"}, False)["group"] == "started"
    assert importer.map_section_to_state({"name": "In Review"}, True)["group"] == "completed"


def test_parent_order_is_deterministic_and_cycle_safe():
    tasks = [{"gid": "child", "parent": {"gid": "parent"}}, {"gid": "parent"}]
    assert [task["gid"] for task in importer.order_tasks(tasks)] == ["parent", "child"]
    with pytest.raises(importer.MigrationError, match="cycle"):
        importer.order_tasks([{"gid": "a", "parent": {"gid": "b"}}, {"gid": "b", "parent": {"gid": "a"}}])


def test_multi_membership_is_rejected():
    with pytest.raises(importer.MigrationError, match="multi-project"):
        importer.validate_memberships([{"gid": "t1", "memberships": [{"project": {"gid": "p1"}}, {"project": {"gid": "p2"}}]}])


def test_dangerous_html_and_url_are_removed():
    value = importer.sanitize_html('<script>alert(1)</script><p><a href="javascript:alert(1)">bad</a><strong>ok</strong></p>')
    assert "alert(1)" not in value
    assert "<strong>ok</strong>" in value
    assert importer.safe_http_url("file:///etc/passwd") is None
    assert importer.safe_http_url("http://127.0.0.1/x") is None


def test_provenance_removes_presigned_urls_but_keeps_stable_links():
    value = importer.strip_ephemeral_urls(
        {
            "download_url": "https://s3.amazonaws.com/a?X-Amz-Signature=secret",
            "permanent_url": "https://app.asana.com/0/1/2",
            "token": "never",
        }
    )
    assert "download_url" not in value
    assert value["permanent_url"] == "https://app.asana.com/0/1/2"
    assert "token" not in value


def test_snapshot_preserves_arbitrary_task_keys_and_unprojected_tasks(tmp_path):
    tmp_path.chmod(0o700)
    root = tmp_path / "export"
    root.mkdir(mode=0o700)
    (root / "source").mkdir(mode=0o700)
    (root / "source" / "projects").mkdir(mode=0o700)
    (root / "source" / "tasks").mkdir(mode=0o700)
    (root / "source" / "stories").mkdir(mode=0o700)
    (root / "source" / "attachments").mkdir(mode=0o700)
    manifest = {"source_workspace_gid": "w1", "export_complete": True, "projects": [{"gid": "p1", "archived": False}], "tasks": ["t1", "t2"]}
    (root / "source" / "manifest.json").write_text(json.dumps(manifest))
    (root / "source" / "projects" / "p1.json").write_text(json.dumps({"gid": "p1", "name": "P", "sections": []}))
    (root / "source" / "tasks" / "t1.json").write_text(json.dumps({"gid": "t1", "name": "project task", "memberships": [{"project": {"gid": "p1"}}], "custom_unknown": {"preserve": True}}))
    (root / "source" / "tasks" / "t2.json").write_text(json.dumps({"gid": "t2", "name": "my task", "memberships": []}))
    (root / "source" / "my-tasks.json").write_text(json.dumps([{"gid": "t2"}]))
    snapshot = importer.Snapshot(root, "w1")
    assert snapshot.tasks["t1"]["custom_unknown"] == {"preserve": True}
    assert [task["gid"] for task in snapshot.tasks_for(None)] == ["t2"]


def test_token_file_requires_private_regular_file(tmp_path):
    token = tmp_path / "token"
    token.write_text("secret")
    token.chmod(0o600)
    assert importer.read_token_file(token) == "secret"
    token.chmod(0o644)
    with pytest.raises(importer.MigrationError, match="0600"):
        importer.read_token_file(token)


def test_redaction_is_recursive():
    value = importer.redact_secrets({"headers": {"Authorization": "secret"}, "safe": "ok"})
    assert value == {"headers": {"Authorization": "[REDACTED]"}, "safe": "ok"}


def test_private_project_payload_has_no_source_content():
    payload = importer.project_payload({"name": "Real source title", "notes": "private"}, "123", placeholder=True)
    assert payload["name"] == "Migration placeholder 123"
    assert "description" not in payload
    assert payload["external_source"] == importer.EXTERNAL_SOURCE


def test_multipart_does_not_copy_auth_fields(tmp_path):
    file = tmp_path / "x.txt"
    file.write_text("x")
    body, boundary = importer.multipart({"key": "k", "Authorization": "secret"}, file, "text/plain")
    assert b"secret" not in body
    assert boundary.encode() in body


def test_redaction_covers_bearer_and_google_signed_urls():
    value = importer.redact_secrets("Bearer abc https://storage.example/x?X-Goog-Signature=secret")
    assert "abc" not in value
    assert "secret" not in value
    assert "[REDACTED_URL]" in value


def test_pending_payload_mismatch_is_blocked(tmp_path):
    tmp_path.chmod(0o700)
    with importer.Ledger(tmp_path) as ledger:
        ledger.pending("tasks", "t1", {"name": "one"})
        with pytest.raises(importer.MigrationError, match="payload mismatch"):
            ledger.check_pending("tasks", "t1", {"name": "changed"})


class _FakeResponse:
    status = 200

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.value).encode()


class _CoreHTTP:
    """Minimal fake HTTP Plane for a phase=tasks end-to-end test."""

    def __init__(self):
        self.calls = []
        self.project = {"id": "dp1", "name": "Migration placeholder p1", "identifier": "AS" + importer.hashlib.sha256(b"p1").hexdigest()[:8].upper(), "external_source": importer.EXTERNAL_SOURCE, "external_id": "p1", "network": 2}
        self.states = {}
        self.items = {}

    def open(self, request, timeout=120):
        method = request.method
        parsed = urllib.parse.urlsplit(request.full_url)
        path = parsed.path
        query = dict(urllib.parse.parse_qsl(parsed.query))
        payload = json.loads(request.data.decode()) if request.data else {}
        self.calls.append((method, path, payload))
        if method == "GET" and path.endswith("/projects/"):
            # Force a second page so external identity reconciliation is proven complete.
            if query.get("cursor") != "page-2":
                return _FakeResponse({"results": [], "next_cursor": "page-2"})
            return _FakeResponse({"results": [self.project]})
        if method == "POST" and path.endswith("/projects/"):
            return _FakeResponse(self.project)
        if path.endswith("/projects/dp1/") and method == "GET":
            return _FakeResponse(self.project)
        if path.endswith("/projects/dp1/") and method == "PATCH":
            self.project.update(payload)
            return _FakeResponse(self.project)
        if path.endswith("/states/") and method == "GET":
            return _FakeResponse({"results": [self.states[k] for k in sorted(self.states)]})
        if path.endswith("/states/") and method == "POST":
            record = {"id": "ds1", **payload}
            self.states[record["id"]] = record
            return _FakeResponse(record)
        if "/states/ds1/" in path and method == "GET":
            return _FakeResponse(self.states["ds1"])
        if path.endswith("/work-items/") and method == "GET":
            return _FakeResponse({"results": []})
        if path.endswith("/work-items/") and method == "POST":
            record = {"id": "di1", **payload}
            self.items["di1"] = record
            return _FakeResponse(record)
        if "/work-items/di1/" in path and method == "GET":
            return _FakeResponse(self.items["di1"])
        raise AssertionError(f"unexpected fake request: {method} {path} {payload}")


def test_tasks_phase_core_flow_uses_pagination_privacy_and_no_detail_writes(tmp_path):
    tmp_path.chmod(0o700)
    root = tmp_path / "export"
    root.mkdir(mode=0o700)
    for relative in ("source", "source/projects", "source/tasks", "source/stories", "source/attachments"):
        (root / relative).mkdir(mode=0o700)
    (root / "source/manifest.json").write_text(json.dumps({"source_workspace_gid": "w1", "export_complete": True, "full_account_export_complete": False, "scope": {"project": "p1"}, "coverage_gaps": [{"kind": "account-wide-unavailable"}], "projects": [{"gid": "p1", "archived": True}], "tasks": ["t1"]}))
    (root / "source/projects/p1.json").write_text(json.dumps({"gid": "p1", "name": "Source Project", "archived": True, "sections": [{"gid": "s1", "name": "In Review"}]}))
    (root / "source/tasks/t1.json").write_text(json.dumps({"gid": "t1", "name": "Core task", "memberships": [{"project": {"gid": "p1"}, "section": {"gid": "s1", "name": "In Review"}}], "custom_unknown": {"keep": True}}))
    (root / "source/stories/t1.json").write_text("[]")
    (root / "source/attachments/t1.json").write_text(json.dumps([{"gid": "a1", "name": "private.bin"}]))
    (root / "source/my-tasks.json").write_text("[]")
    snapshot = importer.Snapshot(root, "w1")
    http = _CoreHTTP()
    client = importer.PlaneClient("token", "dest", opener=http, sleep_fn=lambda _seconds: None)
    with importer.Ledger(root) as ledger:
        result = importer.Importer(snapshot, client, ledger).import_project("p1", phase="tasks")
        assert result["full_verification"] is False
        assert result["archived"] is False
        assert result["details_pending"] == 1
        assert ledger.data["detail_pending"]["t1"]["attachments"] == 1
    assert http.project["name"] == "Source Project"
    assert http.project["network"] == 0
    assert http.states["ds1"]["group"] == "started"
    assert any(method == "PATCH" and payload == {"network": 0} for method, _path, payload in http.calls)
    assert not any("comments" in path or "attachments" in path for _method, path, _payload in http.calls)
    network_patch = next(i for i, (_m, path, payload) in enumerate(http.calls) if path.endswith("/projects/dp1/") and payload == {"network": 0})
    source_patch = next(i for i, (_m, path, payload) in enumerate(http.calls) if path.endswith("/projects/dp1/") and payload.get("name") == "Source Project")
    assert network_patch < source_patch
