#!/usr/bin/env bash
# Static policy guardrails; does not claim model behavior or latency improvements.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 - "$ROOT/prompts/paseo-orchestrator.md" <<'PY'
import sys
from pathlib import Path
prompt = Path(sys.argv[1]).read_text()
assert len(prompt) < 4500, 'Shared prompt exceeded its character budget'
for contract in (
    'For a delegated leaf task',
    'no agents, task-tracker mutations, integration, or scope expansion',
    'no child by default',
    'at most two parallel readers',
    'one writer per checkout/worktree',
    'Fresh context by default',
    'Prefer async with completion notification',
    'fresh independent reviewer for security/data-integrity risks',
    'explicitly approved self-hosted endpoint',
    'Claim speed or quality gains only from measurements',
):
    assert contract in prompt, f'Missing policy contract: {contract}'
assert 'You are the parent engineering orchestrator' not in prompt
print(f'Orchestration policy: static guardrails ok ({len(prompt)} chars)')
PY
