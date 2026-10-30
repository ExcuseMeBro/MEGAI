#!/usr/bin/env python3
"""Acceptance-only verification of the 2026-10-30 local Brokan migration.

Run after reconciliation and selective vault cleanup. Does not write live state.
"""
import hashlib
import json
import os
import sqlite3
import sys
import tomllib
from pathlib import Path

HOME = Path.home()
VAULT = HOME / 'Movies/PROJECTTASKS'
BACKUP = HOME / '.local/share/brokan-migration-backups/megai-582-20261030'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert (VAULT / 'TEMADA').is_dir(), 'TEMADA must survive'
    assert {p.name for p in VAULT.iterdir()} == {'TEMADA'}, 'Only TEMADA may remain in PROJECTTASKS'
    expected_temada = json.loads((BACKUP / 'temada-before.json').read_text())
    actual_temada = {}
    for p in sorted((VAULT / 'TEMADA').rglob('*')):
        key = str(p.relative_to(VAULT / 'TEMADA'))
        actual_temada[key] = (dict(type='symlink', target=os.readlink(p)) if p.is_symlink()
                              else dict(type='dir') if p.is_dir()
                              else dict(type='file', sha256=sha256(p), size=p.stat().st_size))
    assert actual_temada == expected_temada, 'TEMADA entries or bytes changed'
    expected_archive = (BACKUP / 'projecttasks-before.sha256').read_text().split()[0]
    assert sha256(BACKUP / 'projecttasks-before.tar.gz') == expected_archive, 'legacy vault backup corrupted'
    receipt = json.loads((BACKUP / 'reconciliation-receipt.json').read_text())
    assert receipt['known'] == 578 and receipt['legacy_source_count'] == 586
    assert len(receipt['created']) == 8 and len(receipt['changed']) == 3
    assert receipt['temada_manifest_sha256'] == sha256(BACKUP / 'temada-before.json')
    assert receipt['backup_db_sha256'] == sha256(BACKUP / 'brokan-before.db')
    assert (HOME / '.pi/agent/AGENTS.md').read_text().find('Brokan (local kanban, MCP server `brokan`) is the sole execution tracker') >= 0
    assert (HOME / '.codex/AGENTS.md').read_text().find('Brokan (local kanban) is the sole execution tracker') >= 0
    for policy in (HOME / '.pi/agent/AGENTS.md', HOME / '.codex/AGENTS.md',
                   HOME / '.pi/agent/prompts/mdev.md', HOME / '.pi/agent/prompts/prdev.md'):
        assert 'Pellet' not in policy.read_text(), f'stale task authority in {policy}'
    for retired in (HOME / 'Library/Application Support/Pellet', HOME / 'Library/Preferences/com.buildraai.pellet.plist',
                    Path('/Applications/Pellet.app'), HOME / '.config/megai/codex-pellet-mcp.py',
                    HOME / '.megai/lib/pellet_plane_sync.py', HOME / '.megai/lib/plane_pellet_import.py',
                    HOME / '.pi/agent/cache/jiti/megai-layerfs-index.958792f1.mjs',
                    HOME / '.pi/agent/cache/jiti/megai-layerfs-index.afb96130.mjs'):
        assert not retired.exists(), f'retired Pellet runtime/cache persists: {retired}'
    assert (BACKUP / 'pellet-runtime-removal-receipt.json').exists()
    pi_servers = json.loads((HOME / '.pi/agent/mcp.json').read_text())['mcpServers']
    assert 'pellet' not in pi_servers and pi_servers['brokan'].get('enabled', True) is True
    codex = tomllib.loads((HOME / '.codex/config.toml').read_text())
    servers = codex['mcp_servers']
    assert 'pellet' not in servers and servers['brokan']['command'] == 'brokan'
    assert servers['brokan'].get('enabled') is True and servers['plane']['enabled'] is False
    db = sqlite3.connect(f'file:{HOME / "brokan/brokan.db"}?mode=ro', uri=True)
    assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
    task_count = db.execute('select count(*) from tasks').fetchone()[0]
    assert task_count >= 587, 'expected 578 mirrors + 8 source additions + migration task; unrelated newer tasks are retained'
    assert db.execute('select count(*) from tasks where description like ?', ('**PELLET READ-ONLY MIRROR%',)).fetchone()[0] == 0
    for rel, entry in receipt['created'].items():
        row = db.execute('select t.description,p.slug,t.priority from tasks t join projects p on p.id=t.project_id where t.id=?', (entry['id'],)).fetchone()
        assert row and entry['sha256'] in row[0] and row[1] == rel.split('/')[0].lower(), f'missing migrated task: {rel}'
        assert row[2] == entry['priority'], f'priority lost: {rel}'
    for rel, digest in receipt['changed'].items():
        row = db.execute('select description from tasks where description like ?', (f'%Original vault path: `{rel}`%',)).fetchall()
        assert len(row) == 1 and digest in row[0][0], f'changed source not carried: {rel}'
    db.close()
    print(f'PASS: Brokan {task_count} tasks (at least 587), 8 new and 3 changed source records, Pi/Codex configs, private backups, TEMADA unchanged, legacy vault removed')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, KeyError, ValueError, sqlite3.Error) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1)
