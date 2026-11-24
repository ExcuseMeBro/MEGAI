import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { blockReason, checkPush, checkSize, diffLimit, findDevPushes, guardEnabled, sizeReason, toolCommands } from './guard.mjs';

// Blocks a `git push` to dev whose commits weaken tests, unless a commit carries a
// `Test-Change:` trailer, and a push larger than an active diff budget (a Factory routine's
// maxDiffLines or MEGAI_DIFF_LIMIT). Codemode scripts reach bash through nested tool calls,
// which pass through this hook too; `ipython` cells are checked through the shell commands
// visible in their source (bash('…'), os.system, subprocess argv lists). It reads Git only;
// it never edits, retries or pushes.
export default function (pi: ExtensionAPI) {
  pi.on('tool_call', (event: any, ctx: any) => {
    try {
      if (!guardEnabled()) return;
      const commands = toolCommands(event).filter(command => /\bpush\b/.test(command));
      if (!commands.length) return;
      const cwd = ctx?.cwd ?? process.cwd();
      const pushes = commands.flatMap(command => findDevPushes(command, cwd));
      const findings = pushes.flatMap(checkPush);
      if (findings.length) return { block: true, reason: blockReason(findings) };
      const limit = diffLimit();
      const oversize = limit ? pushes.flatMap(push => checkSize(push, limit)) : [];
      if (oversize.length) return { block: true, reason: sizeReason(oversize) };
    } catch {
      // Fail open: a guard error never blocks ordinary work.
    }
  });
}
