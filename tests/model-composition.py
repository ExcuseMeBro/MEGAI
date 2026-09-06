#!/usr/bin/env python3
"""Policy/installation checks, not an LLM quality or throughput benchmark."""
import argparse
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
relative = Path('skills/model-composition/routing.md')
policy = (root / relative).read_text()
assert len(policy) < 5000, 'Routing reference exceeded its bounded size'
rows = [line for line in policy.splitlines() if line.startswith('| ') and '`' in line]
expected = [
    ('User-facing parent: scope, acceptance, decisions, integration', 'openai-codex/gpt-6-astra', 'high'),
    ('Bounded read-only discovery/research', 'minimax/MiniMax-M3', 'medium'),
    ('Routine implementation with a known seam and observable tests', 'minimax/MiniMax-M3', 'high'),
    ('High-risk implementation: auth, permissions, payments, concurrency, data/schema migrations, compatibility', 'openai-codex/gpt-5.6-luna', 'high'),
    ('Complex debugging, independent review, architecture/security advice', 'openai-codex/gpt-5.6-sol', 'high'),
    ('M3 unavailable, failed validation, or context not cleared for MiniMax', 'openai-codex/gpt-5.6-luna', 'medium for read-only; high for writing'),
]
assert len(rows) == len(expected)
for row, assignment in zip(rows, expected):
    cells = [cell.strip().strip('`') for cell in row.strip('|').split('|')]
    assert cells == list(assignment), row
for contract in [
    'System/developer instructions and repository restrictions win',
    'public or explicitly owner-approved non-sensitive repository context',
    'Unknown classification goes to Luna',
    'blanket approval across their public/private projects',
    'M3 is the default for routine delegated tasks',
    'Check the returned model identity',
    'not credentials, personal/production data or private session transcripts',
    'Repository-specific restrictions still win',
    'https://api.minimax.io/anthropic',
    'not proof of authentication, throughput or task quality',
    'Use only medium or high thinking',
    'Tiny known-seam work stays with the parent',
    'one scoped worker replaces parent implementation',
    'fresh context', 'Exactly one writer per checkout',
    'Stop the current writer before a model handoff',
    'fresh Sol review', 'No mandatory Astra → M3 → Luna → Sol chain',
    'Keep existing tests', 'Children never mutate trackers',
    'separate explicit user approval', 'do not poll running agents',
    'TPS alone is not task quality',
]:
    assert contract in policy, f'Missing contract: {contract}'
print('Model composition policy PASS (static; no model-quality claim)')

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true', help='Check this user installation without contacting any provider')
parser.add_argument('--settings-backup', type=Path)
args = parser.parse_args()
if args.live:
    home = Path.home()
    installed = home / '.megai' / relative
    assert installed.read_text() == policy, 'Installed routing differs from source'
    agent = home / '.pi/agent'
    instructions = (agent / 'AGENTS.md').read_text()
    assert str(installed) in instructions
    assert 'Route read-only `scout` and `researcher` to Pi `openai-codex/gpt-5.6-luna`' not in instructions
    assert 'PASEO_AGENT_ID' in instructions and 'completed=false' in instructions
    assert 'minimax/MiniMax-M3' in instructions and 'all projects' in instructions
    assert 'non-sensitive source in all projects, public and private' in instructions
    assert 'secrets, personal/production data and private transcripts remain excluded' in instructions
    assert 'stricter repository rules win' in instructions
    settings = json.loads((agent / 'settings.json').read_text())
    expected_defaults = {'defaultProvider': 'openai-codex', 'defaultModel': 'gpt-6-astra', 'defaultThinkingLevel': 'high'}
    for key, value in expected_defaults.items():
        assert settings.get(key) == value, key
    sub = settings['subagents']
    assert sub['defaultThinking'] == 'medium' and sub['maxThinking'] == 'high'
    m3 = 'minimax/MiniMax-M3'
    regular = ('scout', 'researcher', 'delegate', 'worker')
    for role in regular:
        assert sub['agentOverrides'][role]['model'] == m3, f'{role} still defaults to another model'
        assert sub['agentOverrides'][role]['thinking'] == ('high' if role == 'worker' else 'medium')
        assert m3 in sub['modelScope']['agents'][role]['allow']
    for role in ('reviewer', 'debugger', 'oracle'):
        assert sub['agentOverrides'][role]['model'] == 'openai-codex/gpt-5.6-sol'
        assert sub['agentOverrides'][role]['thinking'] == 'high'
        assert sub['modelScope']['agents'][role]['allow'] == ['openai-codex/gpt-5.6-sol']
    assert sub['modelScope']['enforce'] is True and sub['modelScope']['strict'] is True
    assert m3 in sub['modelScope']['allow']
    assert sub['defaultModel'] == m3, 'M3 must be the routine native default, not merely allowed'
    assert not sub.get('agentOverridesByProvider'), 'Provider overrides need separate routing verification'
    if args.settings_backup:
        before = json.loads(args.settings_backup.read_text())
        # Normalize only the explicitly requested native profile changes; exact
        # comparison then catches unrelated tools, models, scopes or config drift.
        prior = before['subagents']
        prior['defaultModel'] = m3
        for role in regular:
            prior['agentOverrides'][role]['model'] = m3
        assert settings == before, 'Unrelated settings changed'
    print('Live pointer/defaults/source parity PASS; no credentials read or provider requests made')
