#!/usr/bin/env bash
# Policy contract only: no live Plane calls or local execution-board access.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "${1:-$ROOT/task-flow/skills/megai-task-flow/SKILL.md}" <<'PY'
from pathlib import Path
import sys
text = Path(sys.argv[1]).read_text()
rule = 'automatically create exactly one item without asking for approval'
assert text.count(rule) == 1, 'missing or duplicate automatic-create rule'
creation = next(line for line in text.splitlines() if rule in line)
for required in ('Zero matches after a successful complete lookup:', 'that exact title',
                 'resolved `In Progress` state UUID', 'Failed or incomplete lookup is never zero matches.'):
    assert required in creation, required
for forbidden in ('ask approval to create', 'after approval create', 'approved new item', 'create the approved item'):
    assert forbidden not in text, forbidden
for required in ('never create a project implicitly', 'group=started', 'before retrying',
                 'external_id=GID', 'external_source=asana-migration-v1',
                 'never create a replacement', 'in review', 'only the user'):
    assert required.lower() in text.lower(), required
assert 'multiple: ask' in text or 'Multiple matches: stop and ask' in text
print('PASS: missing tasks auto-create; identity, pagination, error and user-only Done guards retained')
PY
