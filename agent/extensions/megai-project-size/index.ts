import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { createMonitor } from './measure.mjs';

// Local, read-only, advisory disk alert for every Pi project. No daemon or deletes.
export default function (pi: ExtensionAPI) {
  let monitor: ReturnType<typeof createMonitor> | undefined;
  function active(ctx: { hasUI: boolean; cwd: string; ui: { notify(message: string, type: 'info' | 'warning' | 'error'): void } }) {
    if (!monitor) monitor = createMonitor({
      emit: (message, type) => {
        if (ctx.hasUI) ctx.ui.notify(message, type);
        else console.error(`[project-size] ${message}`);
      },
    });
    return monitor;
  }
  pi.on('session_start', async (_event, ctx) => { active(ctx).startup(ctx.cwd); });
  pi.on('agent_settled', async (_event, ctx) => { active(ctx).settled(ctx.cwd); });
  pi.on('session_shutdown', async () => { monitor?.shutdown(); monitor = undefined; });
  pi.registerCommand('project-size', {
    description: 'Check this project’s local disk usage and show its largest paths (3 GiB warning threshold)',
    handler: async (_args, ctx) => { await active(ctx).manual(ctx.cwd); },
  });
}
