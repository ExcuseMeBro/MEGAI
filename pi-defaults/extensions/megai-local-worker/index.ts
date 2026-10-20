import { homedir } from 'node:os';
import { join } from 'node:path';
import { getAgentDir, type ExtensionAPI, type ExtensionContext } from '@earendil-works/pi-coding-agent';
import { LocalWorker } from './bridge.mjs';

export default function (pi: ExtensionAPI) {
  function worker(ctx: ExtensionContext) {
    return new LocalWorker({ root: join(process.env.MEGAI_HOME || join(homedir(), '.megai'), 'local-workers'),
      cwd: ctx.cwd, launcher: join(homedir(), '.local/bin/pi-durable'), agentDir: getAgentDir(),
      provider: ctx.model?.provider, model: ctx.model?.id, thinking: pi.getThinkingLevel() });
  }
  function show(value: unknown) {
    pi.sendMessage({ customType: 'local-durable-worker', content:
      'Local native Pi durable worker (not Vercel Workflow World). No current-session migration.\n' + JSON.stringify(value, null, 2),
      display: true }, { triggerTurn: false });
  }
  async function confirm(ctx: ExtensionContext, title: string, text: string) {
    if (!ctx.hasUI) throw new Error('Explicit human UI confirmation required; use the standalone CLI intentionally in headless mode');
    return ctx.ui.confirm(title, text);
  }
  function command(name: string, description: string, handler: (args: string, ctx: ExtensionContext) => Promise<void>) {
    pi.registerCommand(name, { description, handler: async (args, ctx) => {
      try { await handler(args, ctx); } catch (error) { ctx.ui.notify(String(error), 'error'); }
    } });
  }
  command('durable', 'Local durable worker help; explicit jobs only, no daemon or session migration', async (_args, _ctx) => {
    show({ commands: ['/durable-init NAME', '/durable-doctor NAME', '/durable-run NAME REQUEST_ID PROMPT',
      '/durable-status NAME', '/durable-resume NAME', '/durable-stop NAME'],
      policy: 'Read-only tools only. Init/run/resume/stop require human confirmation. Stable request IDs are never blindly relaunched. Selected provider/model/thinking must match on run/resume. Results/logs remain private on disk. No extension/tool/permission parity with this session; no OS filesystem sandbox. No boot service. Mac must be running.' });
  });
  command('durable-init', 'Initialize a read-only worker with the exact current model: /durable-init NAME', async (args, ctx) => {
    const job = worker(ctx), name = args.trim(); job.task(name); job.validateSelection();
    if (await confirm(ctx, 'Initialize local durable worker?',
      `${job.task(name)}\nDirectory: ${job.cwd}\nModel: ${ctx.model?.provider}/${ctx.model?.id}\nThinking: ${pi.getThinkingLevel()}\nRead-only tools. Uses existing agent auth/catalog without copying or changing it. This does not migrate the current session or enable writes.`)) show(await job.init(name));
  });
  command('durable-status', 'Read worker metadata, not its transcript: /durable-status NAME', async (args, ctx) => {
    show(await worker(ctx).inspect(args.trim()));
  });
  command('durable-doctor', 'Check exact model/auth availability, without a model request: /durable-doctor NAME', async (args, ctx) => {
    show(await worker(ctx).inspect(args.trim(), true));
  });
  command('durable-run', 'Start explicit local read-only work: /durable-run NAME STABLE_REQUEST_ID PROMPT', async (args, ctx) => {
    const match = args.trim().match(/^(\S+)\s+(\S+)\s+([\s\S]+)$/);
    if (!match) throw new Error('Usage: /durable-run NAME STABLE_REQUEST_ID PROMPT');
    const job = worker(ctx); job.config(match[1]);
    if (await confirm(ctx, 'Start local durable worker?',
      `${job.task(match[1])}\nRequest: ${match[2]}\n${match[3]}\n\nUses your pinned provider credentials and may incur normal model costs. Read-only tools; no settings or session changes. Worker continues if this Pi session exits. Reusing this request ID never blindly relaunches it.`)) {
      show(await job.launch(match[1], { requestId: match[2], prompt: match[3] }));
    }
  });
  command('durable-resume', 'Explicitly resume retained work: /durable-resume NAME', async (args, ctx) => {
    const job = worker(ctx), name = args.trim(); job.config(name);
    if (await confirm(ctx, 'Resume this local worker?', `${job.task(name)}\nContinue its existing active request, not a new one. May incur model costs. Unsafe work remains blocked; this command cannot reconcile it.`)) show(await job.launch(name, { resume: true }));
  });
  command('durable-stop', 'Cooperative stop of this named worker only: /durable-stop NAME', async (args, ctx) => {
    const job = worker(ctx), name = args.trim(); job.config(name, false);
    if (await confirm(ctx, 'Stop this local worker?', `${job.task(name)}\nRequest a cooperative stop of the run currently owning this exact worker. Retain pending work. No Pi/Paseo session, app, server or IDE is signaled or closed.`)) show(await job.stop(name));
  });
  // No tools, events, session hooks, automatic process start/restart or shutdown signals.
}
