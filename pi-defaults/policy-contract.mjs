import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

// Install-time diagnostic only: textual policy checks are not an OS permission boundary.
// Keep the contract small and explicit so an old profile cannot appear verified
// while it instructs agents to bypass the current task/delivery authority.
export function policyProblems(policy) {
  if (typeof policy !== 'string') return ['missing Pi policy'];
  const required = [
    ['Pellet task authority', /Pellet(?: \([^)]*\))? is the sole execution tracker and\s+acceptance authority/],
    ['no task synchronization', /Do not synchronize Pellet tasks with Plane/],
    ['formal gate preservation', /Guarded safety\/installer\/acceptance changes retain their formal gate and frozen criteria/],
    ['review status', /`in-review`/],
    ['isolated implementation', /verified task-owned worktree/],
    ['source-current checks', /source-current/],
    ['verified local integration', /git merge --ff-only --no-overwrite-ignore <FULL_TASK_SHA>/],
    ['exact remote dev push', /git push <VERIFIED_REMOTE> <FULL_SHA>:refs\/heads\/dev/],
    ['independent remote verification', /git ls-remote/],
    ['session protection', /Never terminate, signal, archive, restart or close/],
  ];
  const obsolete = [
    ['Plane-only task authority', /Plane \(`brodev`\) is the only task tracker|Plane \(workspace brodev\) alone owns execution tracking/],
    ['retired task sync guidance', /\/splane|only\s+Plane\s+sync\s+boundary|syncs?\s+(?:task\s+data\s+with\s+)?Plane/i],
    ['retired workflow launcher', /Before project changes load `pi-workflow`/],
    ['retired discovery as default', /Use task-owned Codedb first/],
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
