import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import {
  CUSTOM_TYPE, buildNudge, classifyFinal, fingerprint, isGptModel, isQuestionPrompt, maxFromEnv, modeFromEnv,
} from './keep-going-core.mjs';

// When a (GPT) model ends a run early (asks for permission, announces the next step
// without doing it, hands back a plan or a list of remaining work, soft-refuses, or
// says it changed nothing) this requests a bounded number of continuations with a
// short "decide and finish" nudge. It never runs tools, changes settings or the model.
// The budget is derived from the transcript, so it survives reloads and restarts.
const EDIT_TOOLS = new Set(['edit', 'write', 'multi_edit', 'apply_patch', 'codemode']);
// Custom messages that start a new unit of work, with a fresh budget (a Factory task).
const SEGMENT_TYPES = new Set(['megai-factory']);

function textOf(content: unknown): string {
  if (typeof content === 'string') return content;
  if (!Array.isArray(content)) return '';
  return content
    .filter((c: any) => c && c.type === 'text' && typeof c.text === 'string')
    .map((c: any) => c.text)
    .join('\n');
}

const toolCalls = (m: any): any[] => (Array.isArray(m?.content) ? m.content.filter((c: any) => c?.type === 'toolCall') : []);
const isOwn = (m: any) => m?.role === 'custom' && m.customType === CUSTOM_TYPE;

/** Decide on one settle boundary. Exported for tests. */
export function decide(event: any, model: any, env: NodeJS.ProcessEnv = process.env) {
  const mode = modeFromEnv(env);
  if (mode === 'off') return null;
  if (mode === 'gpt' && !isGptModel(model)) return null;
  if (event?.outcome !== 'completed' || event.continue) return null;
  const preview = event.context;
  // canContinue is false after a final assistant reply; the appended
  // custom_message is what makes the next provider request valid.
  if (!preview || (preview.pendingMessages?.length ?? 0) > 0) return null;

  // contextMessages keep custom messages (agentmemory recall, this nudge) as role
  // "custom", so the last "user" is the real prompt; llmMessages folds them into
  // user turns. Fall back to llmMessages only if the preview lacks them.
  const messages: any[] = preview.contextMessages?.length ? preview.contextMessages : (preview.llmMessages ?? []);
  let start = -1;
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i];
    if (m?.role === 'user' || (m?.role === 'custom' && SEGMENT_TYPES.has(m.customType))) { start = i; break; }
  }
  if (start < 0) return null;
  if (messages[start].role === 'user' && isQuestionPrompt(textOf(messages[start].content))) return null;

  const segment = messages.slice(start + 1);
  const max = maxFromEnv(env);
  const nudges = segment.filter(isOwn).length;
  if (nudges >= max) return null;

  const assistants = segment.filter((m) => m?.role === 'assistant');
  const final = assistants[assistants.length - 1];
  if (!final || toolCalls(final).length) return null;
  const finalText = textOf(final.content);

  if (nudges > 0) {
    // Since the last nudge: the same reply again, or a second text-only answer in a
    // row, means the model is not moving; stop instead of looping.
    const lastOwn = segment.map(isOwn).lastIndexOf(true);
    const before = segment.slice(0, lastOwn).filter((m) => m?.role === 'assistant').at(-1);
    const after = segment.slice(lastOwn + 1);
    if (before && fingerprint(textOf(before.content)) === fingerprint(finalText)) return null;
    const textOnly = !after.some((m) => m?.role === 'assistant' && toolCalls(m).length);
    if (textOnly && nudges > 1) {
      const prevOwn = segment.map(isOwn).lastIndexOf(true, lastOwn - 1);
      const between = segment.slice(prevOwn + 1, lastOwn);
      if (!between.some((m) => m?.role === 'assistant' && toolCalls(m).length)) return null;
    }
  }

  const calls = assistants.flatMap(toolCalls);
  const edited = calls.some((c: any) => EDIT_TOOLS.has(String(c.name ?? '').toLowerCase()));
  const reason = classifyFinal(finalText, { edited, toolsRan: calls.length > 0 });
  if (!reason) return null;
  return { reason, round: nudges + 1, max };
}

export default function (pi: ExtensionAPI) {
  pi.on('agent_before_settle', (event: any, ctx: any) => {
    try {
      const verdict = decide(event, ctx?.model);
      if (process.env.MEGAI_KEEP_GOING_DEBUG) {
        console.error('[keep-going]', JSON.stringify({ outcome: event?.outcome, cont: event?.continue, pending: event?.context?.pendingMessages?.length, model: ctx?.model && { p: ctx.model.provider, id: ctx.model.id }, verdict }));
      }
      if (!verdict) return;
      return {
        entries: [...(event.entries ?? []), {
          type: 'custom_message', customType: CUSTOM_TYPE, display: true,
          content: buildNudge(verdict.reason, verdict.round, verdict.max),
          details: verdict,
        }],
        continue: true,
      };
    } catch {
      return; // fail open: never break settlement
    }
  });
}
