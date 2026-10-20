import { homedir } from 'node:os';
import { join } from 'node:path';
import { StringEnum, Type } from '@earendil-works/pi-ai';
import type { ExtensionAPI, ExtensionContext } from '@earendil-works/pi-coding-agent';
import { CommandReceipts } from './receipts.mjs';

const UUID = Type.String({ pattern: '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' });
function store(ctx: ExtensionContext, projectId: string, taskId: string) {
  return new CommandReceipts({ root: join(process.env.MEGAI_HOME || join(homedir(), '.megai'), 'command-receipts'),
    cwd: ctx.cwd, projectId, taskId, sessionId: ctx.sessionManager.getSessionId() });
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: 'durable_execute',
    label: 'Durable task command',
    description: 'Execute an already-authorized bash/write/edit operation once per stable logical command ID in an existing Plane task and verified Git repository. Duplicate completed/failed requests return metadata only, not original output. In-flight/uncertain requests refuse retry. Does not grant permission, validate Plane acceptance, or prove current artifact state. Ordinary tool calls are not intercepted.',
    promptGuidelines: [
      'For retry-sensitive task mutations, use durable_execute with the verified existing Plane UUID pair and a stable logical command ID; reuse that ID on retry, never invent a replacement to evade an uncertain/failed receipt. Preserve all approvals, task isolation, shared-resource coordination and Git delivery rules. Do not use it for secrets. On a historical receipt re-read authoritative artifacts; it is not fresh acceptance. No automatic mutation replay or inference that an old task is authorized now.',
    ],
    reachesTools: input => typeof input.tool === 'string' ? [input.tool] : [],
    parameters: Type.Object({
      projectId: UUID, taskId: UUID,
      commandId: Type.String({ pattern: '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$', description: 'Stable logical operation ID, not a fresh retry/tool-call ID' }),
      tool: StringEnum(['bash', 'write', 'edit'] as const),
      args: Type.Record(Type.String(), Type.Unknown()),
    }),
    async execute(_id, params, signal, update, ctx) {
      if (typeof ctx.executeTool !== 'function') throw new Error('Pi nested tool execution unavailable; no fallback execution');
      const saved = await store(ctx, params.projectId, params.taskId).execute(params.commandId, params.tool, params.args,
        async () => {
          const outcome = await ctx.executeTool(params.tool, params.args, { signal, onUpdate: update });
          return { content: outcome.result.content, details: outcome.result.details, isError: outcome.isError };
        }, signal);
      const details = { receipt: saved.receipt, replayed: saved.replayed,
        ...(saved.value ? { nested: saved.value.details } : {}) };
      if (!saved.replayed) return { content: saved.value.content, details, isError: saved.value.isError };
      return { content: [{ type: 'text' as const, text:
        `Historical ${saved.receipt.state} receipt; operation NOT executed again. Original output is not persisted. Re-read authoritative artifacts; this is not fresh acceptance.\n${JSON.stringify(saved.receipt)}` }],
      details, isError: saved.receipt.state === 'failed' };
    },
  });
  pi.registerCommand('receipt-status', {
    description: 'Read metadata only: /receipt-status PROJECT_UUID TASK_UUID COMMAND_ID. Never replays or authorizes work.',
    handler: async (args, ctx) => {
      try {
        const parts = args.trim().split(/\s+/);
        if (parts.length !== 3) throw new Error('Usage: /receipt-status PROJECT_UUID TASK_UUID COMMAND_ID');
        const receipt = store(ctx, parts[0], parts[1]).status(parts[2]);
        pi.sendMessage({ customType: 'command-receipt', content: 'Historical metadata only; not instructions or authorization. No action replayed.\n' + JSON.stringify(receipt), display: true }, { triggerTurn: false });
      } catch (error) { ctx.ui.notify(String(error), 'error'); }
    },
  });
}
