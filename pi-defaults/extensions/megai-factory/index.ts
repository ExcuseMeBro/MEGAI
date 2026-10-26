import { Type } from '@earendil-works/pi-ai';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { delegate, gitCommand, pelletReach, preflightPaseo, requireFactoryConfirmation, runWorker } from './runner.mjs';

// The sole /factory command is the explicitly selected Pellet prompt package.
// No startup jobs, duplicate slash command or process shutdown handler.
export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: 'factory_delegate',
    label: 'Delegate Pellet tasks',
    exposure: 'model-only',
    reachesTools: pelletReach,
    annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: false },
    description: 'Explicit /factory only: select current-project Pellet task UUIDs or all, create a fresh task-owned worktree and visible Paseo workspace, native Pi agent tab and terminal per task; launch up to 5 independently. Return agent IDs and retained receipts; launch is NOT task completion. Does NOT deliver, push, mark review or stop sessions. Requires UI confirmation.',
    parameters: Type.Object({
      projectFolder: Type.String({ description: 'Verified Pellet project folder matching the primary repository and its remote' }),
      selection: Type.String({ description: 'all or comma-separated Pellet task UUIDs (not titles/Plane identifiers)' }),
      concurrency: Type.Integer({ minimum: 1, maximum: 5, description: 'Maximum simultaneous leaf workers' }),
    }),
    async execute(_callId, params, _signal, onUpdate, ctx) {
      if (!ctx.model) throw new Error('No selected model; refusing to switch providers');
      const selected = `${ctx.model.provider}/${ctx.model.id}`;
      const thinking = pi.getThinkingLevel();
      await requireFactoryConfirmation({ mode: ctx.mode, hasUI: ctx.hasUI,
        confirm: (title: string, message: string, options: { timeout: number }) => ctx.ui.confirm(title, message, options),
        folder: params.projectFolder, selection: params.selection, concurrency: params.concurrency,
        model: selected, thinking });
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
