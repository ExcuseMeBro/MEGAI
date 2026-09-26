#!/usr/bin/env bash
# Static policy contract; actual Git ownership/delivery needs runtime evidence.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -B - "$ROOT" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
profile = (root / 'pi-defaults/AGENTS.md').read_text()
workflow = (root / 'pi-defaults/skills/pi-workflow/SKILL.md').read_text()
lifecycle = (root / 'skills/agent-worktree-lifecycle/SKILL.md').read_text()
for text, required in (
    (profile, ('separate, verified task-owned worktree', 'never edit, stage or commit task source in the dev/main checkout',
               'reserve integration targets through `megai queue`', 'Main/push/publishing still need separate explicit approval')),
    (workflow, ('native `git worktree add`', 'Never edit/stage/commit task source on dev/main',
                'Reserve integration targets through `megai queue`', 'Main promotion and push require separate explicit approval')),
    (lifecycle, ('Every Git source writer uses a separate task-owned worktree',
                'If identity or exclusive ownership is uncertain, block Git writes',
                'Reserve all integration targets atomically with `megai queue`',
                'remove only a released, clean, task-owned worktree', 'Do not use force')),
):
    for clause in required:
        assert clause in text, f'Missing policy contract: {clause}'
    assert 'pa' + 'seo' not in text.lower()
print('Isolated native-Git delivery: static policy checks passed')
PY
