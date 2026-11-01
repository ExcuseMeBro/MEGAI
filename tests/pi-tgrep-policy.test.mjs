import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { guardBroadSearch } from '../pi-defaults/extensions/tgrep/search-policy.mjs';

const bash = (command) => ({ toolName: 'bash', input: { command } });

test('Pi blocks common broad recursive grep before traversal, even with post-filter', () => {
  for (const command of [
    'grep -rl "config" ~/Documents ~/PROJECTS | grep -v node_modules',
    'grep -R -l config .',
    'grep --recursive --files-with-matches config "$HOME/PROJECTS"',
    'printf ready && grep -rn config /Users/example/PROJECTS',
  ]) {
    const decision = guardBroadSearch(bash(command));
    assert.equal(decision?.block, true, command);
    assert.match(decision.reason, /tgrep|scope/i, command);
  }
});

test('targeted grep, complete rg, other shell commands and non-bash tools remain unchanged', () => {
  for (const command of [
    'grep -rl config src', 'grep -rl config test/fixtures',
    'rg -n config .', 'rg -uuu config .', 'tgrep --no-index -n -F config src',
    'echo "grep -r config ~/PROJECTS"', 'grep -rn config /tmp/fixtures',
  ]) assert.equal(guardBroadSearch(bash(command)), undefined, command);
  assert.equal(guardBroadSearch({ toolName: 'read', input: { path: '~/PROJECTS' } }), undefined);
});

test('installed tgrep source registers the guard at the Pi tool-call boundary', () => {
  const source = readFileSync(new URL('../pi-defaults/extensions/tgrep/index.ts', import.meta.url), 'utf8');
  assert.match(source, /pi\.on\(["']tool_call["']/);
  assert.match(source, /guardBroadSearch\(event\)/);
  assert.doesNotMatch(source, /user_bash|setActiveTools|setModel/);
});
