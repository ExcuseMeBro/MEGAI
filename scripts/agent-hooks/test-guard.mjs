#!/usr/bin/env node
// PreToolUse adapter for Claude Code and Codex around Pi's megai-test-guard.
// Blocks a `git push` to dev whose range weakens tests (unless a commit has a
// `Test-Change:` trailer) or exceeds an active MEGAI_DIFF_LIMIT. The guard logic is
// imported live from ~/.pi/agent/extensions/megai-test-guard/guard.mjs.
// Fails open: any error allows the tool call. Block = exit 2 with the reason on stderr.
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

function commandOf(input) {
  const t = input?.tool_input ?? {};
  for (const key of ['command', 'cmd', 'script']) {
    const v = t[key];
    if (typeof v === 'string') return v;
    if (Array.isArray(v)) return v.join(' ');
  }
  return '';
}

try {
  const input = JSON.parse(readFileSync(0, 'utf8') || '{}');
  const command = commandOf(input);
  if (/\bpush\b/.test(command)) {
    const g = await import(pathToFileURL(join(homedir(), '.pi/agent/extensions/megai-test-guard/guard.mjs')).href);
    if (g.guardEnabled()) {
      const pushes = g.findDevPushes(command, input.cwd || process.cwd());
      const findings = pushes.flatMap(g.checkPush);
      let reason = findings.length ? g.blockReason(findings) : '';
      if (!reason) {
        const limit = g.diffLimit();
        const oversize = limit ? pushes.flatMap((p) => g.checkSize(p, limit)) : [];
        if (oversize.length) reason = g.sizeReason(oversize);
      }
      if (reason) {
        process.stderr.write(reason + '\n');
        process.exit(2);
      }
    }
  }
} catch {
  // Fail open.
}
process.exit(0);
