"""Offline regression proof for the retained, unwired one-off importer."""
import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "lib"))
import asana_plane_import as migration  # noqa: E402


@pytest.fixture
def ledger(tmp_path):
    tmp_path.chmod(0o700)
    with migration.Ledger(tmp_path) as value:
        yield value


def snapshot(**extra):
    return SimpleNamespace(coverage_gaps=[], full_account_export_complete=True, scope={}, **extra)


@pytest.mark.parametrize("version", [None, 1])
@pytest.mark.parametrize("network", [None, 0, 1, 2])
def test_project_resume_reproves_privacy_before_ledger_upgrade(ledger, version, network):
    current = {"id": "dp1", "external_source": migration.EXTERNAL_SOURCE, "external_id": "p1", "network": network}
    old = {"id": "dp1", "fingerprint_version": version, "readback_hash": migration.owned_fingerprint("projects", current)}
    ledger.complete("projects", "p1", old)
    before = copy.deepcopy(ledger.data)
    worker = migration.Importer(snapshot(), SimpleNamespace(project=lambda _id: current), ledger)
    if network == 0:
        assert worker.ensure_project("p1", {"name": "Source"}) == current
        assert old["fingerprint_version"] == 1
    else:
        with pytest.raises(migration.MigrationError, match="not private"):
            worker.ensure_project("p1", {"name": "Source"})
        assert ledger.data == before


@pytest.mark.parametrize("kind", ["states", "labels"])
@pytest.mark.parametrize("version", [None, 1])
@pytest.mark.parametrize("drift", [False, True])
def test_definition_resume_preserves_established_fingerprint(ledger, kind, version, drift):
    key = "dp1:started" if kind == "states" else "dp1:tag1"
    current = {"id": "d1", "project_id": "dp1", "external_source": migration.EXTERNAL_SOURCE, "external_id": key, "name": "In Progress" if kind == "states" else "Tag", "group": "started", "color": "#64748b"}
    old = {"id": "d1", "origin": "created", "fingerprint_version": version, "readback_hash": migration.owned_fingerprint(kind, current)}
    ledger.complete(kind, key, old)
    before = copy.deepcopy(ledger.data)
    if drift:
        current["description"] = "destination edit" if kind == "labels" else None
        if kind == "states":
            current["color"] = "#ffffff"
    client = SimpleNamespace(slug="dest", request=lambda method, path: current)
    worker = migration.Importer(snapshot(), client, ledger)

    def resume():
        if kind == "states":
            return worker.ensure_state("dp1", {"gid": "s1", "name": "In Progress"}, False)
        return worker.ensure_label("dp1", {"gid": "tag1", "name": "Tag"})

    if version == 1 and drift:
        with pytest.raises(migration.ConflictError, match="drift"):
            resume()
        assert ledger.data == before
    else:
        resume()
        assert old["fingerprint_version"] == 1
        assert old["readback_hash"] == migration.owned_fingerprint(kind, current)


@pytest.mark.parametrize("bundle", [False, True])
@pytest.mark.parametrize("failure", [None, "missing", "id", "metadata", "source", "checksum", "unsafe-url"])
def test_attachment_resume_reads_destination_and_checksum(ledger, tmp_path, monkeypatch, bundle, failure):
    source_gid = "t1:migration-record" if bundle else "a1"
    file = tmp_path / "attachment"
    file.write_bytes(b"source")
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    receipt = {"sha256": digest, "bytes": file.stat().st_size, "name": "attachment"}
    monkeypatch.setattr(migration, "_validate_receipt", lambda *_args: (file, receipt))
    monkeypatch.setattr(migration.socket, "getaddrinfo", lambda *_args, **_kwargs: [(None, None, None, None, ("8.8.8.8", 443))])
    destination = {"id": "da1", "external_id": source_gid, "external_source": migration.EXTERNAL_SOURCE, "name": "attachment", "download_url": "https://bucket.s3.amazonaws.com/file"}
    ledger.complete("attachments", source_gid, {"id": "da1", "sha256": "old" if failure == "source" else digest, "fingerprint_version": 1, "readback_hash": migration.owned_fingerprint("attachments", destination)})
    if failure == "id":
        destination["id"] = "other"
    if failure == "metadata":
        destination["name"] = "changed"
    if failure == "unsafe-url":
        destination["download_url"] = "http://127.0.0.1/private"
    reads = []

    def work_item(project_id, task_id):
        reads.append((project_id, task_id))
        return {"attachments": [] if failure == "missing" else [destination]}

    def checksum(url):
        reads.append(url)
        return "wrong" if failure == "checksum" else digest

    worker = migration.Importer(snapshot(), SimpleNamespace(work_item=work_item, download_checksum=checksum), ledger)

    def resume():
        if bundle:
            worker.import_attachment_file("dp1", "dt1", source_gid, file, "application/json", digest)
        else:
            worker.import_attachment("dp1", "dt1", {"gid": source_gid})

    if failure:
        with pytest.raises(migration.MigrationError):
            resume()
    else:
        resume()
        assert reads == [("dp1", "dt1"), "https://bucket.s3.amazonaws.com/file"]
    assert reads[0] == ("dp1", "dt1")


@pytest.mark.parametrize("pending", [None, "pending", "detail_pending"])
@pytest.mark.parametrize("phase", ["tasks", "all"])
def test_identity_only_verification_never_claims_full_preservation(ledger, pending, phase):
    if pending:
        ledger.data[pending] = {"t1": {}}
    result = migration.Importer(snapshot(), SimpleNamespace(), ledger).verify(phase=phase)
    assert result["status"] == "partial"
    assert result["full_verification"] is False
    assert result["verification_scope"] == "core_identity_only"
    assert "attachments/checksums" in result["unverified"]
    assert result["pending"] == int(pending == "pending")
    assert result["details_pending"] == int(pending == "detail_pending")


def test_import_readbacks_do_not_claim_full_verification(ledger, monkeypatch):
    source = snapshot(project_detail=lambda _gid: {"archived": False}, tasks_for=lambda _gid: [])
    worker = migration.Importer(source, SimpleNamespace(), ledger)
    monkeypatch.setattr(worker, "ensure_project", lambda *_args: {"id": "dp1"})
    monkeypatch.setattr(worker, "verify_cached_definitions", lambda _id: None)
    for result in (worker.import_project("p1"), worker.import_my_tasks()):
        assert result["full_verification"] is False
        assert result["verification_scope"] == "import_readbacks_only"


@pytest.mark.parametrize("drift", [False, True])
def test_comment_resume_rechecks_owned_content(ledger, monkeypatch, drift):
    story = {"gid": "c1", "resource_subtype": "comment_added", "text": "Hello", "created_by": {"name": "Author"}, "created_at": "date"}
    source = snapshot(task_stories=lambda _gid: [story], attachments=lambda _gid: [])
    current = {"id": "dc1", "external_source": migration.EXTERNAL_SOURCE, "external_id": "c1", "comment_html": "<p><strong>Original Asana comment by Author at date</strong></p><p>Hello</p>"}
    ledger.complete("comments", "c1", {"id": "dc1", "fingerprint_version": 1, "readback_hash": migration.owned_fingerprint("comments", current)})
    if drift:
        current["comment_html"] = "Destination edit"
    worker = migration.Importer(source, SimpleNamespace(slug="dest", comment=lambda *_args: current), ledger)
    monkeypatch.setattr(worker, "ensure_state", lambda *_args: {"id": "s1"})
    monkeypatch.setattr(worker, "_ensure", lambda *_args: {"id": "dt1"})
    monkeypatch.setattr(worker, "import_bundle", lambda *_args: None)
    monkeypatch.setattr(migration, "_metadata_bundle", lambda *_args: {})
    if drift:
        with pytest.raises(migration.MigrationError, match="mismatch"):
            worker.import_task("p1", "dp1", {"gid": "t1"}, {})
    else:
        worker.import_task("p1", "dp1", {"gid": "t1"}, {})


def test_verify_cli_partial_result_is_nonzero(tmp_path, monkeypatch, capsys):
    tmp_path.chmod(0o700)
    monkeypatch.setattr(migration, "Snapshot", lambda *_args: snapshot(root=tmp_path))
    monkeypatch.setattr(migration, "read_token_file", lambda _path: "fake")
    monkeypatch.setattr(migration, "PlaneClient", lambda *_args: SimpleNamespace())
    result = migration.main(["verify", "--source", str(tmp_path), "--source-workspace-gid", "w1", "--workspace-slug", "dest", "--token-file", "unused"])
    assert result == 2
    assert json.loads(capsys.readouterr().out)["full_verification"] is False
