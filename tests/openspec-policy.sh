#!/usr/bin/env bash
# Static guardrails, not proof of model compliance. Negative mutations ensure
# each required clause is independently checked rather than implied by a name.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "$ROOT/skills/megai-openspec/SKILL.md" <<'PY'
from pathlib import Path
import sys
skill = Path(sys.argv[1]).read_text()
contracts = {
    'small-fix bypass': 'Do not initialize OpenSpec or generate artifacts for these tasks unless requested.',
    'one checklist': 'the single detailed implementation checklist, `tasks.md`',
    'no tracker duplication': 'Do not mirror individual tasks into Asana or `.todos`.',
    'version mismatch': 'On any version mismatch, stop and escalate to the parent before running the workflow',
    'real tests': "Run the task's actual regression tests and relevant diagnostics/build.",
    'user-only Done': 'Only the user may mark Asana Done.',
    'archive approval': 'Archive only after explicit user approval of that change and passing verification.',
    'separate promotion': 'neither archive nor a checked checklist authorizes Asana Done or main promotion.',
}
def missing(text):
    return [name for name, clause in contracts.items() if clause not in text]
assert not missing(skill), missing(skill)
for name, clause in contracts.items():
    assert skill.count(clause) == 1, f'Duplicated guardrail: {name}'
    assert missing(skill.replace(clause, '', 1)) == [name], name
print(f'OpenSpec policy: {len(contracts)} guardrails and negative mutations passed')
PY
