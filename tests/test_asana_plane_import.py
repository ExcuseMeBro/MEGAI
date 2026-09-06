import json
import sys
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
