// Independent completion check for megai-keep-going. A cheap model on the session's
// own provider reads the request, the final reply and a compact list of tool calls
// and says whether the run is done. The transcript never goes to another provider
// unless MEGAI_KEEP_GOING_JUDGE names one explicitly. Every failure means "no verdict".

export const DEFAULT_JUDGES = ['gpt-6-luna', 'gpt-5.6-luna', 'gpt-5-nano', 'claude-haiku-5-5'];
const LIMIT = { request: 4000, reply: 4000, call: 160, calls: 40, missing: 300 };
export const JUDGE_TIMEOUT_MS = 20_000;

export const SYSTEM = [
  'You check whether an autonomous coding agent finished the user\'s request before it stopped.',
  'The agent has standing approval for routine engineering: code, tests, refactors, dev-branch delivery, task-tracker updates.',
  'Answer with one JSON object only: {"verdict": "done" | "continue" | "blocked" | "question", "missing": "<one short sentence>"}.',
  '"done": the requested work is implemented and verified (or the request was small and is fully answered).',
  '"continue": the agent stopped while work it could do itself remains: it announced next steps, left a plan or a partial change, skipped verification it could run, asked permission for routine work, or delivered less than asked.',
  '"blocked": the remaining step needs something only the user has (a secret, credentials, a decision with real-world consequences) or a reserved approval (main/release/tag/force push, production data, real money, spending), and the agent said so.',
  '"question": the user only asked a question or an opinion and wanted no changes, and it was answered.',
  'Judge from the evidence below only. When unsure between done and continue, answer done. "missing" names the concrete unfinished item for "continue", else "".',
].join('\n');

const cut = (text, n) => {
  const t = String(text ?? '');
  return t.length > n ? `${t.slice(0, n / 2)}\n…\n${t.slice(-n / 2)}` : t;
};

function summarizeCall(call) {
  let args = '';
  try { args = typeof call.arguments === 'string' ? call.arguments : JSON.stringify(call.arguments ?? {}); } catch { args = ''; }
  return `${call.name ?? 'tool'}: ${cut(args.replace(/\s+/g, ' '), LIMIT.call)}`;
}

/** The judge's user message. */
export function buildJudgeInput({ request, reply, calls = [], edited = false }) {
  const list = calls.slice(-LIMIT.calls).map(summarizeCall);
  const skipped = Math.max(0, calls.length - LIMIT.calls);
  return [
    '## User request', cut(request, LIMIT.request),
    `## Tool calls in this run (${calls.length}${skipped ? `, first ${skipped} omitted` : ''}; files edited: ${edited ? 'yes' : 'no'})`,
    list.length ? list.join('\n') : '(none)',
    '## Agent\'s final reply', cut(reply, LIMIT.reply),
  ].join('\n\n');
}

/** Strict parse of the judge's reply; anything else is no verdict. */
export function parseVerdict(text) {
  const match = /\{[\s\S]*\}/.exec(String(text ?? ''));
  if (!match) return null;
  let value;
  try { value = JSON.parse(match[0]); } catch { return null; }
  if (!value || !['done', 'continue', 'blocked', 'question'].includes(value.verdict)) return null;
  const missing = typeof value.missing === 'string' ? value.missing.replace(/\s+/g, ' ').trim().slice(0, LIMIT.missing) : '';
  return { verdict: value.verdict, missing };
}

/**
 * Choose the judge model. MEGAI_KEEP_GOING_JUDGE=off disables, =provider/id picks one
 * explicitly; by default the first cheap model on the session's provider with auth.
 */
export function pickJudge(registry, sessionModel, env = process.env) {
  const setting = String(env.MEGAI_KEEP_GOING_JUDGE ?? '').trim();
  if (/^(?:0|off|false|none)$/i.test(setting)) return undefined;
  // The session's own provider already authenticates the running session.
  const usable = (m) => m && (m.provider === sessionModel?.provider || typeof registry.hasConfiguredAuth !== 'function' || registry.hasConfiguredAuth(m));
  if (setting) {
    const slash = setting.indexOf('/');
    if (slash < 1) return undefined;
    const model = registry.find(setting.slice(0, slash), setting.slice(slash + 1));
    return usable(model) ? model : undefined;
  }
  const provider = sessionModel?.provider;
  if (!provider) return undefined;
  for (const id of DEFAULT_JUDGES) {
    const model = registry.find(provider, id);
    if (usable(model)) return model;
  }
  return undefined;
}

/** Ask the judge; resolves to a verdict or null, never rejects. */
export async function runJudge(registry, model, input, signal) {
  const timeout = AbortSignal.timeout(JUDGE_TIMEOUT_MS);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;
  try {
    const stream = registry.streamSimple(model, {
      systemPrompt: SYSTEM,
      messages: [{ role: 'user', content: [{ type: 'text', text: input }], timestamp: Date.now() }],
    }, { signal: combined, reasoning: 'low', maxTokens: 1500 });
    const message = await stream.result();
    if (!message || message.stopReason === 'error' || message.stopReason === 'aborted') return null;
    const text = (message.content ?? []).filter((c) => c?.type === 'text').map((c) => c.text).join('\n');
    return parseVerdict(text);
  } catch {
    return null;
  }
}
