// Shared classifier for the MEGAI keep-going nudge (Pi extension and Codex Stop hook).
// It decides whether a final assistant message ended the turn by asking for
// permission/confirmation, or by reporting that no change was made, instead of
// finishing the work. Pure functions only: no I/O, no model calls.

export const CUSTOM_TYPE = 'megai-keep-going';

export const NUDGE = [
  '[megai keep-going] You ended the turn by asking for permission/confirmation or without making the change, instead of finishing.',
  'Routine work is pre-approved: pick the most reasonable option yourself (from the code, existing patterns and the request),',
  'state the assumption in one line, and carry the task through to completion now (code, tests, delivery per AGENTS.md).',
  'Stop and ask only if the next step is irreversible (production data, real money movement, main/release push, spending)',
  'or needs something only the user has (a secret, an offline machine): then finish everything else first and ask once, briefly.',
  'If the user only asked a question or an opinion and wanted no changes, reply with one short line and stop.',
].join(' ');

const L = '\\p{L}\\p{N}_';
// Unicode-aware whole-word pattern (JS \b is ASCII-only, Uzbek/Russian need \p{L}).
const w = (src) => new RegExp(`(?<![${L}])(?:${src})(?![${L}])`, 'iu');

// Permission/confirmation for the task itself: always a premature stop.
const STRONG = [
  // English
  w("(?:shall|should|can|may) i\\s[^.!?\\n]{0,160}\\?"),
  w("should we\\s[^.!?\\n]{0,160}\\?"),
  w("(?:do|would) you (?:want|like) me to"),
  w("want me to\\s[^.!?\\n]{0,160}\\?"),
  w("(?:please )?confirm(?: (?:that|whether|which|if|the|this))?[^.!\\n]{0,120}\\?"),
  w("(?:please )?(?:approve|give (?:me )?the go-ahead|say the word)"),
  w("(?:ready|happy) to (?:proceed|implement|start|continue)[^.!\\n]{0,80}(?:\\?|when you|once you|if you)"),
  w("(?:proceed|continue|go ahead)\\s*\\?"),
  w("(?:your|the) (?:permission|approval|go-ahead|sign-off|ok)[^.!\\n]{0,120}\\?"),
  w("(?:with|once i have|after) your (?:permission|approval|go-ahead|confirmation)"),
  // Uzbek: first-person/inclusive question suffixes and direct requests
  w("[\\p{L}']+(?:aymi|aylikmi|amizmi)"),
  w("(?:xohlaysiz|istaysiz|tasdiqlaysiz|ruxsat berasiz|rozimisiz)mi|maqulmi"),
  w("tasdiqlang|ruxsat bering|aniqlashtirib ber(?:ing)?"),
  // Russian
  w("(?:продолж|сдела|запуст|начат|начн|внес|примен)[\\p{L}]*\\s*\\?"),
  w("(?:хотите|желаете|подтвердите|подтверждаете)"),
];

// Offers / hand-backs: a stop only when the run changed nothing (after finished
// work, "if you want I can also…" is a normal closing, not a refusal).
const SOFT = [
  w("would you like (?:me )?to"),
  w("let me know (?:if|whether|which|how|what|when)"),
  w("if you(?:'d| would)? (?:like|want|prefer)[,]? i (?:can|could|will)"),
  w("deb yozing|ayting|aytsangiz|kerakmi\\s*\\?|bo'ladimi\\s*\\?"),
  w("скажите|дайте знать"),
];

const NOT_DONE = [
  w("no (?:code |source |file )?changes? (?:were |was |have been |has been )?(?:made|applied|written|committed)"),
  w("(?:i )?(?:have not|haven't|did not|didn't) (?:yet )?(?:made|make|changed?|modif(?:y|ied)|edit(?:ed)?|writ(?:e|ten)|touch(?:ed)?|implement(?:ed)?)(?: any)? (?:code|changes?|files?|anything|it)"),
  w("nothing (?:was|has been|is) (?:changed|modified|edited|implemented|written)"),
  w("kod(?:ga|ni)?\\s+(?:hali\\s+)?(?:o'zgartirilmagan|o'zgartirilmadi|tegilmadi|tegmadim|yozilmadi)"),
  w("o'zgartirish kiritilmadi|o'zgartirish kiritilmagan|hech narsa o'zgartirilmadi|hech narsa o'zgartirilmagan"),
  w("код (?:не (?:изменён|изменен|менял|тронут)|пока не (?:изменён|изменен))|изменения не внесены|ничего не (?:менял|изменено|изменял)"),
];

/** Normalize apostrophe variants (o‘zgartirish / o'zgartirish) and strip code. */
export function normalize(text) {
  return String(text ?? '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`\n]*`/g, ' ')
    .replace(/[‘’ʻʼ`´]/g, "'");
}

/** Only the ending decides: a question in the middle of a report is not a stop. */
export function ending(text, chars = 700) {
  const t = normalize(text).trim();
  return t.length > chars ? t.slice(-chars) : t;
}

/**
 * @param {string} text final assistant text
 * @param {{ edited?: boolean }} [opts] edited: the run already changed files
 * @returns {'ask' | 'not-done' | null}
 */
export function classifyFinal(text, opts = {}) {
  const tail = ending(text);
  if (!tail) return null;
  if (STRONG.some((re) => re.test(tail))) return 'ask';
  if (opts.edited) return null;
  if (SOFT.some((re) => re.test(tail))) return 'ask';
  if (NOT_DONE.some((re) => re.test(tail))) return 'not-done';
  return null;
}

/** A user prompt that is itself a question may legitimately get a question back. */
export function isQuestionPrompt(prompt) {
  const t = normalize(prompt).trim();
  return t.endsWith('?');
}

/** MEGAI_KEEP_GOING=0 disables, =all applies to every model; default: GPT/OpenAI only. */
export function modeFromEnv(env = process.env) {
  const v = String(env.MEGAI_KEEP_GOING ?? '').trim().toLowerCase();
  if (v === '0' || v === 'off' || v === 'false') return 'off';
  if (v === 'all') return 'all';
  return 'gpt';
}

export function isGptModel(model) {
  if (!model) return false;
  const provider = String(model.provider ?? '').toLowerCase();
  const id = String(model.id ?? model.modelId ?? '').toLowerCase();
  return /openai|codex|azure/.test(provider) || /(?:^|[/-])(?:gpt|codex|o[1-9])(?:[-.]|$)/.test(id) || id.includes('gpt');
}
