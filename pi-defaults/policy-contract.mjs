import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

// Install-time diagnostic only: textual policy checks are not an OS permission boundary.
// Keep the contract small and explicit so an old profile cannot appear verified
// while it instructs agents to bypass the current task/delivery authority.
export function policyProblems(policy) {
  if (typeof policy !== 'string') return ['missing Pi policy'];
  const required = [
    ['Brokan task authority', /Brokan(?: \([^)]*\))? is the sole execution tracker and\s+acceptance authority/],
    ['no task synchronization', /Do not synchronize Brokan tasks with Plane/],
    ['formal gate preservation', /Guarded safety\/installer\/acceptance changes retain their formal gate and frozen criteria/],
    ['review status', /Brokan status `review`/],
    ['isolated implementation', /task-owned worktree/],
    ['source-current checks', /source-current/],
    ['standing dev delivery approval', /STANDING APPROVAL/],
    ['sync with dev before merge', /git rebase dev/],
    ['verified local integration', /git merge --ff-only task\/<slug>/],
    ['exact remote dev push', /git push <remote> dev/],
    ['independent remote verification', /git merge-base --is-ancestor <FULL_SHA> <remote>\/dev/],
    ['task branch cleanup', /git worktree remove <path>[\s\S]*git branch -d task\/<slug>/],
    ['targeted session stop', /`kill <PID>`[\s\S]*never use broad `pkill`\/`killall`/],
    ['uncommitted work is committed', /Uncommitted changes are never discarded, reset or stashed away: commit them/],
  ];
  const obsolete = [
    ['Plane-only task authority', /Plane \(`brodev`\) is the only task tracker|Plane \(workspace brodev\) alone owns execution tracking/],
    ['retired task sync guidance', /\/splane|only\s+Plane\s+sync\s+boundary|syncs?\s+(?:task\s+data\s+with\s+)?Plane/i],
    ['retired Pellet authority', /Pellet(?: \([^)]*\))? is the sole execution tracker and\s+acceptance authority/],
    ['retired workflow launcher', /Before project changes load `pi-workflow`/],
    ['retired discovery as default', /Use task-owned Codedb first/],
    // These clauses made models stop and wait for a human instead of merging to dev.
    ['approval-blocked dev delivery', /auto-merge\/rebase|Unknown\/unrelated ahead commits, dirty\/busy target|divergence needs explicit reconciliation|An active or uncertain task worktree must be RETAINED|Never terminate, signal, archive, restart or close/],
  ];
  return [
    ...required.filter(([, pattern]) => !pattern.test(policy)).map(([label]) => `missing: ${label}`),
    ...obsolete.filter(([, pattern]) => pattern.test(policy)).map(([label]) => `obsolete: ${label}`),
  ];
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  const problems = policyProblems(readFileSync(process.argv[2], 'utf8'));
  if (problems.length) {
    console.error(`Pi policy contract rejected: ${problems.join('; ')}`);
    process.exitCode = 1;
  }
}
