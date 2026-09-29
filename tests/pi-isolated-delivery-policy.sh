#!/usr/bin/env bash
# Static policy contract, not proof of unattended runtime execution.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 -B - "$ROOT" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
profile = (root / 'pi-defaults/AGENTS.md').read_text()
workflow = (root / 'pi-defaults/skills/pi-workflow/SKILL.md').read_text()
lifecycle = (root / 'skills/agent-worktree-lifecycle/SKILL.md').read_text()
for text, requirements in (
    (profile, ('For every Git change, including one-line fixes',
               'Never edit\nsource, stage or commit directly on the dev/main checkout',
               'automatically reserves\nthe integration target',
               'without asking the user again',
               'best bounded solution and continue rather than stopping',
               'wait no more than one\nminute',
               'Main promotion, push and publishing still require separate\nexplicit approval')),
    (workflow, ('This\n   applies even to tiny edits',
                'automatically deliver verified task commits to local dev',
                'without waiting for another user confirmation',
                'Push only with separate explicit approval',
                'Automatically archive only released, clean, task-owned temporary workspaces',
                'No background daemon, hook, unattended main merge')),
    (lifecycle, ('Every Git\nchange, however small',
                 'If isolated ownership cannot be proved, stop Git edits',
                 'the only permitted task-related change in the primary dev checkout',
                 'automatically run\n   **Post-merge cleanup**',
                 'never force/reset another task',
                 'Only `finish --outcome completed` after',
                 'Delete only the recorded safely merged local task branch')),
):
    for requirement in requirements:
        assert requirement in text, f'Missing policy contract: {requirement}'
assert 'Paseo-managed task worktree when estimated' not in profile
assert 'Smaller work → a clean' not in profile
assert "Overrides pi-workflow\nstep 3's per-task Paseo requirement" not in profile
print('Isolated dev delivery: static policy checks passed')
PY
