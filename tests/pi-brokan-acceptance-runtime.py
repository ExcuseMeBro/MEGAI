#!/usr/bin/env python3
"""Read-only local verification of Brokan acceptance wiring; never queries Plane."""
import hashlib
import json
from pathlib import Path
import tomllib
import urllib.request

HOME = Path.home()
BACKUP = HOME / '.local/share/brokan-migration-backups/megai-582-20261030'
OLD_APPROVAL = BACKUP / 'acceptance-contract.json'
BOOTSTRAP = BACKUP / 'bootstrap-gate/contract.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert digest(OLD_APPROVAL) == '03fe5f1df30482bae9cb5d188ae360a2f876a4434ad8a3d576f5a7e415c5cb59'
    assert digest(BOOTSTRAP) == 'ebe0e05e37a312bcd7ed9865b3335826bdd24a9e8e977b0c6ba575994808412f'
    with urllib.request.urlopen('http://127.0.0.1:1317/api/tasks/582', timeout=4) as response:
        task = json.load(response)['task']
    assert task['id'] == 582 and task['project'] == 'megai' and task['status'] in ('doing', 'review')
    servers = json.loads((HOME / '.pi/agent/mcp.json').read_text())['mcpServers']
    assert 'brokan' in servers and servers['brokan'].get('enabled', True)
    assert 'plane' not in servers and 'pellet' not in servers
    codex = tomllib.loads((HOME / '.codex/config.toml').read_text())['mcp_servers']
    assert 'brokan' in codex and codex['brokan'].get('enabled', True)
    assert 'plane' not in codex and 'pellet' not in codex
    policy = (HOME / '.pi/agent/AGENTS.md').read_text()
    assert 'Brokan (local kanban, MCP server `brokan`) is the sole execution tracker' in policy
    assert 'frozen Brokan schema-4 contract' in ' '.join(policy.split())
    skill = (HOME / '.pi/agent/skills/pi-workflow/SKILL.md').read_text()
    assert 'Brokan is the sole task tracker and acceptance authority' in skill
    assert 'pi-workflow start --title' not in skill
    acceptance = (HOME / '.pi/agent/skills/megai-acceptance/SKILL.md').read_text()
    assert 'Use schema 4 and `brokan.task_id`' in acceptance
    selection = json.loads((HOME / '.pi/agent/settings.json').read_text())['skills']
    assert '+skills/megai-acceptance/SKILL.md' in selection
    assert '+skills/pi-workflow/SKILL.md' in selection
    for path in (HOME / '.local/bin/pi-workflow', HOME / '.pi/agent/defaults/workflow.py',
                 HOME / '.pi/agent/defaults/plane_mcp_headers.py',
                 HOME / '.megai/lib/plane_mcp_headers.py'):
        assert not path.exists(), f'retired installed Plane entrypoint persists: {path}'
    print('PASS: Brokan task available; Pi/Codex MCP, policy, workflow and acceptance use Brokan; historical approvals intact; legacy Plane entrypoints absent')


if __name__ == '__main__':
    main()
