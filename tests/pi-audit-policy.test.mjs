import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const policy = readFileSync(new URL('../pi-defaults/local-profile/minimal-AGENTS.md', import.meta.url), 'utf8');
const docs = readFileSync(new URL('../docs/pi-audit-remediation.md', import.meta.url), 'utf8');

test('compact runtime policy keeps safety/delivery/authority boundaries', () => {
  assert.ok(Buffer.byteLength(policy) < 8000, 'keep the runtime profile bounded');
  for (const fragment of ['Brokan is the sole execution tracker', 'todo then doing', 'Brokan `review`',
    'EVERY delivered commit in remote main', 'task-owned worktree', 'STANDING APPROVAL',
    'never ask "should I merge/push/clean up?"', 'git rebase dev', 'are NOT blockers',
    'git merge --ff-only task/<slug>', 'git push <remote> dev',
    'git merge-base --is-ancestor <FULL_SHA> <remote>/dev', 'git worktree remove <path>',
    'git branch -d task/<slug>', 'git push <remote> --delete task/<slug>',
    'Other branches:', 'Explicit persistent-branch', 'force-push',
    'Uncommitted changes are never discarded', 'wip/<date>-<slug>', '`kill <PID>`',
    'Never stop your own Pi process', 'broad `pkill`/`killall`',
    'private pre-change receipt/backup', 'Guarded safety/acceptance/installer',
    'provider, model and thinking', 'revalidate Brokan task',
    'Reconcile uncertain\nBrokan writes', 'Do not\nre-enable Headroom', '/rwbrowser']) {
    assert.ok(policy.includes(fragment), `missing boundary: ${fragment}`);
  }
  for (const blocker of ['auto-merge/rebase', 'Unknown/unrelated ahead commits',
    'divergence needs explicit reconciliation', 'never infer destructive or publishing approval',
    "discarding someone else's uncommitted work", 'stopping\nuser sessions']) {
    assert.ok(!policy.includes(blocker), `approval-blocking clause returned: ${blocker}`);
  }
  assert.match(policy, /Reuse verified IDs, paths and results/);
  assert.match(policy, /not after every tool/);
  assert.match(policy, /No model\/transport performance claims/);
});

test('remediation documents selective reversible application and non-fabricated A/B', () => {
  for (const fragment of ['opt-in runtime profile', 'SHA256', 'rollback', 'new Pi',
    'session-level', 'first-token', 'at least 5 paired',
    'alternating A/B', 'cold', 'warm', 'p95', 'explicit approval', 'No invented A/B results']) {
    assert.ok(docs.includes(fragment), `missing procedure: ${fragment}`);
  }
});
