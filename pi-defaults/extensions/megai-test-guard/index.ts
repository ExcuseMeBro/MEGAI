import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { blockReason, checkPush, findDevPushes, guardEnabled } from './guard.mjs';

// Blocks a `git push` to dev whose commits weaken tests, unless a commit carries a
// `Test-Change:` trailer. Codemode scripts reach bash through nested tool calls, which
// pass through this hook too. It reads Git only; it never edits, retries or pushes.
export default function (pi: ExtensionAPI) {
  pi.on('tool_call', (event: any, ctx: any) => {
    try {
      if (!guardEnabled() || event?.toolName !== 'bash') return;
      const command = String(event.input?.command ?? '');
      if (!/\bpush\b/.test(command)) return;
      const findings = findDevPushes(command, ctx?.cwd ?? process.cwd()).flatMap(checkPush);
      if (findings.length) return { block: true, reason: blockReason(findings) };
    } catch {
      // Fail open: a guard error never blocks ordinary work.
    }
  });
}
