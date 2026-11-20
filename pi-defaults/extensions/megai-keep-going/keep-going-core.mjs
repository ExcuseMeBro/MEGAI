// Shared classifier for the MEGAI keep-going nudge (Pi extension and Codex Stop hook).
// It decides whether a final assistant message ended the turn early instead of
// finishing the work: asking for permission, announcing the next step without doing
// it, handing back a plan or a list of remaining work, soft-refusing a routine task,
// or reporting that nothing was changed. Pure functions only: no I/O, no model calls.

export const CUSTOM_TYPE = 'megai-keep-going';
export const DEFAULT_MAX = 3;
export const MAX_LIMIT = 8;

const BOUNDARY = 'Stop and ask only if the next step is irreversible (production data, real money movement, main/release/tag/force push, spending) '
  + 'or needs something only the user has (a secret, an offline machine): then finish everything else first and say exactly what is blocked, once.';

const REASONS = {
  ask: 'You ended the turn by asking for permission/confirmation. Routine work is pre-approved: pick the most reasonable option yourself (from the code, existing patterns and the request), state the assumption in one line, and carry on.',
  announce: 'You said what you would do next and then ended the turn without doing it. Do it now, in this turn, with tool calls.',
  plan: 'You returned a plan without executing any of it. Execute the plan now; do not restate it.',
  unfinished: 'Your reply lists work that is still not done. Finish those items now unless one truly needs the user.',
  refusal: 'This is ordinary, authorized engineering on the user\'s own project. Do the full requested work, not a smaller or simplified version. If one specific part is truly impossible, finish every other part and name that part and why in one line.',
  'not-done': 'You reported that no change was made although the request implies one. Make the change now.',
  judge: 'An independent completion check found the request is not finished yet.',
};

/** Continuation text for one nudge; later rounds are firmer. */
export function buildNudge(reason = 'ask', round = 1, max = DEFAULT_MAX, missing = '') {
  const head = `[megai keep-going ${round}/${max} · ${reason}]`;
  const detail = String(missing ?? '').replace(/\s+/g, ' ').trim().slice(0, 300);
  const parts = [head, REASONS[reason] ?? REASONS.ask, ...(detail ? [`Still missing: ${detail}`] : []),
    'Carry the task through to completion now: code, tests, delivery per AGENTS.md.', BOUNDARY];
  if (round > 1) {
    parts.push('This is a repeated stop. Your next message must contain a tool call that advances the task; a text-only reply is acceptable only as the final report of fully finished work or of a reserved blocker.');
  }
  parts.push('If the user only asked a question or an opinion and wanted no changes, or the work is already complete, reply with the short final report and stop.');
  return parts.join(' ');
}

/** Backward-compatible single nudge (Codex Stop hook). */
export const NUDGE = buildNudge('ask', 1, 1);

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
  w("(?:which|what) (?:option|approach|one) (?:do|would) you (?:prefer|like|want|choose)"),
  // Uzbek: first-person/inclusive question suffixes and direct requests
  w("[\\p{L}']+(?:aymi|aylikmi|amizmi)"),
  w("(?:xohlaysiz|istaysiz|tasdiqlaysiz|ruxsat berasiz|rozimisiz)mi|maqulmi"),
  w("tasdiqlang|ruxsat bering|aniqlashtirib ber(?:ing)?"),
  w("qaysi (?:biri|variant|yo'l)[^.!\\n]{0,60}\\?"),
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

// "I'll now do X." as the last sentence of the turn: the work was announced, not done.
// Anchored at the start of that sentence (after a short "Next," style lead-in).
const a = (src) => new RegExp(`^(?:[^.!?\\n]{0,30}[,:]\\s*)?(?:${src})(?![${L}])`, 'iu');
const ANNOUNCE = [
  a("(?:i(?:'ll| will| am going to|'m going to)|let me|now i(?:'ll| will)|next,? i(?:'ll| will)) (?:now |next |then |immediately |go ahead and )?(?:proceed|start|begin|implement|run|create|update|fix|add|write|continue|apply|make|build|refactor|wire|deploy|deliver|commit|push|merge|test|patch|edit|modify|change|investigate|check|look)"),
  a("(?:proceeding|moving on|continuing) (?:to|with)"),
  a("(?:endi|keyin|hozir|navbatda|so'ng)[ ,][^.!?\\n]{0,100}(?:qilaman|boshlayman|yozaman|ishga tushiraman|o'tkazaman|tuzataman|qo'shaman|davom ettiraman|bajaraman|tekshiraman|yangilayman|o'zgartiraman|yarataman)"),
  a("[^.!?\\n]{0,80}(?:qilishni|bajarishni|yozishni|tuzatishni|qo'shishni) boshlayman"),
  a("(?:сейчас|теперь|далее|дальше|затем) (?:я )?(?:сделаю|запущу|исправлю|добавлю|начну|реализую|внесу|обновлю|проверю|перейду)"),
  a("приступаю"),
];

// The reply itself says work is still open.
const UNFINISHED = [
  w("(?:remaining|outstanding|pending|unfinished) (?:work|tasks?|steps?|items?|parts?)\\s*[:\\-]"),
  w("still (?:to do|todo|needs? to be|pending|missing|not (?:done|implemented|wired|finished))"),
  w("not yet (?:implemented|finished|completed|wired(?: up)?|done)|not (?:implemented|finished|completed|wired up|done) yet"),
  w("(?:in|for) a (?:follow-?up|future|later|separate|next) (?:turn|session|step|pr|task|iteration)"),
  w("qolgan (?:ishlar|vazifalar|qadamlar|qism)|hali (?:qilinmagan|bajarilmagan|tugallanmagan|yozilmagan|ulanmagan)|keyingi (?:sessiyada|bosqichda|turnda)"),
  w("осталось (?:сделать|реализовать)|ещё не (?:сделано|реализовано|готово)|в следующ(?:ий|ем) (?:раз|шаге|сессии)"),
];

// "Next steps" style hand-back, a stop only when the run changed nothing.
const NEXT_STEPS = [
  w("(?:next|suggested|recommended) steps?\\s*[:\\-]"),
  w("keyingi qadamlar|tavsiya etilgan qadamlar"),
  w("следующие шаги"),
];

const PLAN = [
  w("(?:here(?:'s| is) (?:the|my) )?(?:implementation |proposed )?plan\\s*[:\\-]"),
  w("(?:reja|план)\\s*:"),
  w("(?:i|we) (?:would|will|can) (?:need to )?(?:do|approach|implement) (?:this|it) (?:as follows|in (?:the following|these) steps)"),
];

// Soft refusals / scope cuts on routine engineering.
const REFUSAL = [
  w("i (?:can(?:'t|not)|am unable to|'m unable to|am not able to|'m not able to|won't be able to) (?:help|assist|do|complete|implement|finish|build|write|make|carry)"),
  w("(?:beyond|outside(?: of)?) (?:the )?(?:scope|capabilit)"),
  w("too (?:large|big|complex|extensive|much) (?:for|to (?:do|complete|finish|implement) in) (?:a single|one|this|the current)"),
  w("(?:would|will) (?:require|take) (?:significant|substantial|considerable|a lot of|much more) (?:time|effort|work)"),
  w("(?:a |as a )?(?:simplified|minimal|basic|skeleton|stub(?:bed)?) (?:version|implementation)[^.!\\n]{0,80}(?:for now|instead|to start)"),
  w("(?:left|leave) (?:this |it )?as an exercise"),
  w("qila olmayman|bajara olmayman|yoza olmayman|imkonim yo'q|juda (?:katta|murakkab) (?:ish|vazifa)"),
  w("не могу (?:помочь|сделать|выполнить|реализовать)|выходит за рамки"),
];

const NOT_DONE = [
  w("no (?:code |source |file )?changes? (?:were |was |have been |has been )?(?:made|applied|written|committed)"),
  w("(?:i )?(?:have not|haven't|did not|didn't) (?:yet )?(?:made|make|changed?|modif(?:y|ied)|edit(?:ed)?|writ(?:e|ten)|touch(?:ed)?|implement(?:ed)?)(?: any)? (?:code|changes?|files?|anything|it)"),
  w("nothing (?:was|has been|is) (?:changed|modified|edited|implemented|written)"),
  w("kod(?:ga|ni)?\\s+(?:hali\\s+)?(?:o'zgartirilmagan|o'zgartirilmadi|tegilmadi|tegmadim|yozilmadi)"),
  w("o'zgartirish kiritilmadi|o'zgartirish kiritilmagan|hech narsa o'zgartirilmadi|hech narsa o'zgartirilmagan"),
  w("код (?:не (?:изменён|изменен|менял|тронут)|пока не (?:изменён|изменен))|изменения не внесены|ничего не (?:менял|изменено|изменял)"),
];

// A stop the user really owns: the reserved-approval list plus things only the user has.
const RESERVED = [
  /^FACTORY_PAUSE$/m,
  w("(?:need|needs|require|requires|missing|provide|without)[^.\\n]{0,60}(?:secret|token|password|passphrase|api[ -]?key|credentials?|2fa|otp|one-time code|pairing code|sudo)"),
  w("(?:push(?:ing)?|merg(?:e|ing)|promot(?:e|ing))[^.\\n]{0,30}(?:to |into )?(?:main|master|release)(?: branch)?"),
  w("force[- ]push|(?:cut|create|publish|tag)(?:ting|ing)? (?:a |the )?(?:release|tag)"),
  w("production (?:data(?:base)?|db|deploy(?:ment)?|server|environment)|prod (?:data|db|deploy)"),
  w("real money|charge (?:the |a )?(?:card|customer)|spend(?:ing)? (?:money|budget|credits)"),
  w("(?:host|server|machine|device)[^.\\n]{0,40}(?:offline|unreachable|not reachable|down)|host key|permission denied \\(publickey"),
  w("parol\\p{L}*|maxfiy kalit|sir(?:li)? kalit|token kerak|main(?:ga)? push|prod(?:uction)?(?:'?(?:ga|da|ni))? (?:ma'lumot|baza)"),
  w("(?:production|prod)\\p{L}*'?\\p{L}* [^.\\n]{0,40}(?:tasdig|ruxsat)|biznes qarori|provayder ruxsati"),
  // Shared-resource gates and running delegates (AGENTS.md: record the pending gate, do not poll).
  w("(?:memory|ram|xotira)[^.\\n]{0,60}(?:block|defer|blok)\\p{L}*|heavy-test (?:lock|slot)|slot (?:is )?busy"),
  w("agent(?:i|lari)?[*_]*\\s+(?:hali\\s+)?(?:ishlamoqda|ishlayapti|ishlashda davom)|(?:delegates?|subagents?|workers?|lanes?) (?:are |is )?still running"),
  w("пароль|секрет|токен (?:нужен|требуется)|прод(?:акшн)? (?:баз|данн)"),
];

/** Normalize apostrophe variants (o‘zgartirish / o'zgartirish) and strip code. */
export function normalize(text) {
  return String(text ?? '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`\n]*`/g, ' ')
    .replace(/"[^"\n]{60,}"/g, ' ') // long quoted text (a drafted prompt) is not the model's own ask
    .replace(/[‘’ʻʼ`´]/g, "'");
}

/** Only the ending decides: a question in the middle of a report is not a stop. */
export function ending(text, chars = 700) {
  const t = normalize(text).trim();
  return t.length > chars ? t.slice(-chars) : t;
}

/** The last two sentences (or lines) of the reply. */
export function lastSentences(text, count = 2) {
  const t = normalize(text).trim();
  const pieces = t.split(/(?<=[.!?…])\s+|\n+/u).map((s) => s.trim()).filter(Boolean);
  return pieces.slice(-count).join(' ');
}

/** The reply names a stop that only the user can clear. */
export function isReservedBlock(text) {
  const tail = ending(text, 1200);
  return RESERVED.some((re) => re.test(tail));
}

/**
 * @param {string} text final assistant text
 * @param {{ edited?: boolean, toolsRan?: boolean }} [opts]
 *   edited: the run already changed files; toolsRan: the run called any tool
 *   (undefined = unknown, plan detection is skipped)
 * @returns {'ask' | 'announce' | 'refusal' | 'unfinished' | 'plan' | 'not-done' | null}
 */
export function classifyFinal(text, opts = {}) {
  const tail = ending(text);
  if (!tail) return null;
  if (isReservedBlock(text)) return null;
  if (STRONG.some((re) => re.test(tail))) return 'ask';
  if (ANNOUNCE.some((re) => re.test(lastSentences(text, 1)))) return 'announce';
  if (REFUSAL.some((re) => re.test(tail))) return 'refusal';
  if (UNFINISHED.some((re) => re.test(tail))) return 'unfinished';
  if (opts.edited) return null;
  if (SOFT.some((re) => re.test(tail))) return 'ask';
  if (NOT_DONE.some((re) => re.test(tail))) return 'not-done';
  if (NEXT_STEPS.some((re) => re.test(tail))) return 'unfinished';
  if (opts.toolsRan === false && PLAN.some((re) => re.test(ending(text, 3000)))) return 'plan';
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

/** MEGAI_KEEP_GOING_MAX: continuations per prompt (1..8, default 3). */
export function maxFromEnv(env = process.env) {
  const n = Number.parseInt(String(env.MEGAI_KEEP_GOING_MAX ?? ''), 10);
  if (!Number.isFinite(n) || n < 1) return DEFAULT_MAX;
  return Math.min(n, MAX_LIMIT);
}

export function isGptModel(model) {
  if (!model) return false;
  const provider = String(model.provider ?? '').toLowerCase();
  const id = String(model.id ?? model.modelId ?? '').toLowerCase();
  return /openai|codex|azure/.test(provider) || /(?:^|[/-])(?:gpt|codex|o[1-9])(?:[-.]|$)/.test(id) || id.includes('gpt');
}

/** Comparable form of a reply, to detect a model repeating the same stop. */
export function fingerprint(text) {
  return normalize(text).toLowerCase().replace(/\s+/g, ' ').trim().slice(-400);
}
