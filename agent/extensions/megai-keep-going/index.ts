import type { ExtensionAPI } from '@mariozechner/pi-coding-agent';
import { CUSTOM_TYPE, NUDGE, classifyFinal, isGptModel, isQuestionPrompt, modeFromEnv } from './keep-going-core.mjs';

// When a GPT model ends a run by asking for permission/confirmation (or by saying
// it changed nothing) this requests ONE continuation per user prompt with a short
// "decide and finish" nudge. It never runs tools, changes settings or the model.
const EDIT_TOOLS = new Set(['edit', 'write', 'multi_edit', 'apply_patch', 'codemode']);

function textOf(content: unknown): string {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  return content
    .filter((c: any) => c && c.type === 'text' && typeof c.text === 'string')
    .map((c: any) => c.text)
    .join('\n');
}

export default function (pi: ExtensionAPI) {
  let nudged = false;

  pi.on('before_agent_start', (event: any) => {
    if (event?.messageType === 'user') nudged = false;
  });

  pi.on('agent_before_settle', (event: any, ctx: any) => {
    if (process.env.MEGAI_KEEP_GOING_DEBUG) console.error('[keep-going]', JSON.stringify({ outcome: event?.outcome, cont: event?.continue, can: event?.context?.canContinue, pending: event?.context?.pendingMessages?.length, model: ctx?.model && { p: ctx.model.provider, id: ctx.model.id }, roles: (event?.context?.contextMessages ?? []).map((m: any) => m?.role), nudged }));
    try {
      const mode = modeFromEnv();
      if (mode === 'off' || nudged) return;
      if (mode === 'gpt' && !isGptModel(ctx?.model)) return;
      if (event.outcome !== 'completed' || event.continue) return;
      const preview = event.context;
      // canContinue is false after a final assistant reply; the appended
      // custom_message below is what makes the next provider request valid.
      if (!preview || (preview.pendingMessages?.length ?? 0) > 0) return;

      // contextMessages keep custom messages (agentmemory recall, this nudge) as
      // role "custom", so the last "user" is the real prompt; llmMessages folds them
      // into user turns. Fall back to llmMessages only if the preview lacks them.
      const messages: any[] = preview.contextMessages?.length ? preview.contextMessages : (preview.llmMessages ?? []);
      let lastUser = -1;
      for (let i = messages.length - 1; i >= 0; i--) {
        if (messages[i]?.role === 'user') { lastUser = i; break; }
      }
      if (lastUser < 0 || isQuestionPrompt(textOf(messages[lastUser].content))) return;

      const run = messages.slice(lastUser + 1).filter((m) => m?.role === 'assistant');
      const final = run[run.length - 1];
      if (!final) return;
      const edited = run.some((m) => Array.isArray(m.content) && m.content.some(
        (c: any) => c?.type === 'toolCall' && EDIT_TOOLS.has(String(c.name ?? '').toLowerCase())));
      if (!classifyFinal(textOf(final.content), { edited })) return;

      nudged = true;
      return {
        entries: [...(event.entries ?? []), { type: 'custom_message', customType: CUSTOM_TYPE, content: NUDGE, display: true }],
        continue: true,
      };
    } catch {
      return; // fail open: never break settlement
    }
  });
}
