import { Type } from '@earendil-works/pi-ai';
import { basename } from 'node:path';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { delegate, gitCommand, preflightPaseo, runWorker } from './runner.mjs';

// No hooks, startup jobs, role router or process shutdown handler. This tool runs
// only for an explicit /delegate request, after user confirmation in the TUI.
export default function (pi: ExtensionAPI) {
  pi.registerCommand('delegate', {
    description: 'Opt-in Pellet task delegation: /delegate all or /delegate UUID,UUID [concurrency=1..5]',
    handler: async (args, ctx) => {
      const match = args.trim().match(/^(all|[a-f0-9]{32}(?:,[a-f0-9]{32})*)(?:\s+concurrency=([1-5]))?$/i);
      if (!match) {
        ctx.ui.notify('Usage: /delegate all | UUID,UUID [concurrency=1..5]. No workers started.', 'warning');
        return;
      }
      const projectFolder = basename(ctx.cwd);
      const selection = match[1];
      const concurrency = Number(match[2] ?? 2);
      pi.sendUserMessage(`User explicitly invoked /delegate. Project folder candidate: ${projectFolder}. Selection: ${selection}. Concurrency: ${concurrency}. Verify the project identity and independent Pellet tasks before calling factory_delegate exactly once with {projectFolder, selection, concurrency}. The tool asks for UI confirmation and independently validates every task. Each result is a distinct, still-running or idle Paseo agent tab and terminal in its own visible workspace/worktree; a launch is NOT completion. Report agent/workspace/terminal IDs. Revisit each agent after its work completes, inspect full diffs and source-current tests; serialize all shared delivery with verified remote inclusion and eligible cleanup before updating each task to in-review. Never sync Plane (except /splane), deliver to main, publish, signal/archive user sessions or blindly retry uncertain work.`, { triggerTurn: true });
    },
  });
  pi.registerTool({
    name: 'factory_delegate',
    label: 'Delegate Pellet tasks',
    exposure: 'model-only',
    reachesTools: () => 'mcp__pellet__query_tasks mcp__pellet__get_task mcp__pellet__update_task',
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false },
    description: 'Explicit /delegate only: select current-project Pellet task UUIDs or all, create a fresh task-owned worktree and visible Paseo workspace, native Pi agent tab and terminal per task; launch up to 5 independently. Return agent IDs and retained receipts; launch is NOT task completion. Does NOT deliver, push, mark review or stop sessions. Requires UI confirmation.',
    parameters: Type.Object({
      projectFolder: Type.String({ description: 'Verified Pellet project folder matching the primary repository and its remote' }),
      selection: Type.String({ description: 'all or comma-separated Pellet task UUIDs (not titles/Plane identifiers)' }),
      concurrency: Type.Integer({ minimum: 1, maximum: 5, description: 'Maximum simultaneous leaf workers' }),
    }),
    async execute(_callId, params, _signal, onUpdate, ctx) {
      if (!ctx.hasUI || ctx.mode !== 'tui') throw new Error('Factory delegation requires explicit interactive confirmation; headless calls cannot launch workers');
      if (!ctx.model) throw new Error('No selected model; refusing to switch providers');
      const selected = `${ctx.model.provider}/${ctx.model.id}`;
      const thinking = pi.getThinkingLevel();
      if (!(await ctx.ui.confirm('Launch independent Paseo Pi agents?',
        `Project: ${params.projectFolder}\nTasks: ${params.selection}\nParallel Paseo agents: ${params.concurrency}\nModel: ${selected} (${thinking})\n` +
        'Each selected task gets its own visible Paseo workspace, independent native Pi agent tab, terminal and fresh Git worktree. Agents keep working after this call returns; no shared delivery or session termination. Continue?')))
        throw new Error('User declined factory delegation');
      const call = (name: string, args: unknown) => ctx.executeTool(name, args);
      const results = await delegate({ cwd: ctx.cwd, folder: params.projectFolder, selection: params.selection,
        concurrency: params.concurrency, model: selected, thinking,
        query: (args: unknown) => call('mcp__pellet__query_tasks', args),
        get: (args: unknown) => call('mcp__pellet__get_task', args),
        start: (args: unknown) => call('mcp__pellet__update_task', args),
        git: gitCommand, preflight: (model: string, thinking: string) => preflightPaseo(model, thinking, undefined, ctx.cwd), launch: runWorker,
        progress: (event: { task: string; status: string; worktree: string; receipt: string }) =>
          onUpdate?.({ content: [{ type: 'text', text: JSON.stringify(event) }] }),
      });
      return { content: [{ type: 'text', text: JSON.stringify(results) }], details: results };
    },
  });
}
