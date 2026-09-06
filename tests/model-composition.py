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
    ('openai-codex/gpt-6-astra', 'high'),
    ('minimax/MiniMax-M3', 'medium'),
    ('minimax/MiniMax-M3', 'high'),
    ('openai-codex/gpt-5.6-luna', 'high'),
    ('openai-codex/gpt-5.6-sol', 'high'),
    ('openai-codex/gpt-5.6-luna', 'medium for read-only; high for writing'),
]
assert len(rows) == len(expected)
for row, (model, thinking) in zip(rows, expected):
    cells = [cell.strip().strip('`') for cell in row.strip('|').split('|')]
    assert cells[1:] == [model, thinking], row
for contract in [
    'System/developer instructions and repository restrictions win',
    'public or explicitly owner-approved non-sensitive repository context',
    'Unknown classification goes to Luna',
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
    settings = json.loads((agent / 'settings.json').read_text())
    expected_defaults = {'defaultProvider': 'openai-codex', 'defaultModel': 'gpt-6-astra', 'defaultThinkingLevel': 'high'}
    for key, value in expected_defaults.items():
        assert settings.get(key) == value, key
    sub = settings['subagents']
    assert sub['defaultThinking'] == 'medium' and sub['maxThinking'] == 'high'
    m3 = 'minimax/MiniMax-M3'
    regular = ('scout', 'researcher', 'delegate', 'worker')
    for role in regular:
        assert sub['agentOverrides'][role]['thinking'] == ('high' if role == 'worker' else 'medium')
        assert m3 in sub['modelScope']['agents'][role]['allow']
    for role in ('reviewer', 'debugger', 'oracle'):
        assert sub['agentOverrides'][role]['thinking'] == 'high'
        assert sub['modelScope']['agents'][role]['allow'] == ['openai-codex/gpt-5.6-sol']
    assert sub['modelScope']['enforce'] is True and sub['modelScope']['strict'] is True
    assert m3 in sub['modelScope']['allow']
    assert sub['defaultModel'] == 'openai-codex/gpt-5.6-luna', 'Keep safe GPT fallback unless M3 is explicitly selected'
    if args.settings_backup:
        before = json.loads(args.settings_backup.read_text())
        # Normalize only the explicitly requested native profile changes; exact
        # comparison then catches unrelated tools, models, scopes or config drift.
        prior = before['subagents']
        prior['defaultThinking'], prior['maxThinking'] = 'medium', 'high'
        for role in regular + ('reviewer', 'debugger', 'oracle'):
            prior['agentOverrides'][role]['thinking'] = 'medium' if role in regular[:3] else 'high'
        if m3 not in prior['modelScope']['allow']:
            prior['modelScope']['allow'].append(m3)
        for role in regular:
            allowed = prior['modelScope']['agents'][role]['allow']
            if m3 not in allowed:
                allowed.append(m3)
        assert {k:v for k,v in settings.items() if k not in expected_defaults} == {k:v for k,v in before.items() if k not in expected_defaults}, 'Unrelated settings changed'
    print('Live pointer/defaults/source parity PASS; no credentials read or provider requests made')
