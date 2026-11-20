// Pure helpers for the independent change review. No I/O: unit-tested directly.

export const READ_ONLY_TOOLS = 'read,grep,find,ls';
export const DEFAULT_MODEL = 'openai/gpt-6.2-sol:high';
export const LIMITS = Object.freeze({ total: 120_000, perFile: 20_000, context: 8_000 });

export const LAYERS = [
  ['config & contracts', f => /(^|\/)(package\.json|tsconfig[^/]*\.json|[^/]*\.d\.ts|schema[^/]*|[^/]*\.proto|\.env\.example)$|(^|\/)(migrations?|schemas?|types?)\//i.test(f) || /\/config\.json$|^config\//i.test(f)],
  ['core logic', () => false], // default bucket, resolved below
  ['wiring, I/O & entry points', f => /(^|\/)(index|main|server|cli|app|routes?|router|handlers?|controllers?|api)[^/]*\.[cm]?[jt]sx?$|(^|\/)(api|routes|handlers|controllers|bin|scripts)\//i.test(f) || /\.(py|sh)$/.test(f) && /(^|\/)(main|cli|server|app|manage)\.\w+$|(^|\/)scripts\//.test(f)],
  ['UI', f => /\.(tsx|jsx|vue|svelte|css|scss|html)$|(^|\/)(components|pages|views|ui|dashboard)\//i.test(f)],
  ['tests', f => /(^|\/)(tests?|__tests__|spec)\/|[._-](test|spec)\.[^/]+$|(^|\/)test_[^/]+\.py$/i.test(f)],
  ['docs', f => /\.(md|mdx|rst|txt)$|(^|\/)docs\//i.test(f)],
];
const GENERATED = /(^|\/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|Cargo\.lock|poetry\.lock|go\.sum|[^/]*\.min\.(js|css)|[^/]*\.snap)$|(^|\/)(dist|build|vendor|node_modules)\//;

/** Order files into review layers: contracts first, then logic, wiring, UI, tests, docs. */
export function changeStack(files) {
  const order = [0, 4, 5, 3, 2]; // check tests/docs/UI before wiring so `tests/index.ts` is a test
  const buckets = LAYERS.map(([name]) => ({ name, files: [] }));
  for (const f of files) {
    let hit = 1;
    for (const i of order) if (LAYERS[i][1](f)) { hit = i; break; }
    buckets[hit].files.push(f);
  }
  return buckets.filter(b => b.files.length);
}

export const isGenerated = f => GENERATED.test(f);

const SECRET = /-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(gh[pousr]_[A-Za-z0-9]{16,}|figd_[A-Za-z0-9_-]{16,}|xox[abpr]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,})|\bBearer\s+[A-Za-z0-9._~+\/=-]{12,}|\b(api[_-]?key|secret|token|passw(or)?d|authorization)\b["']?\s*[:=]\s*["']?[A-Za-z0-9._~+\/=-]{12,}/i;

/** Replace secret-looking diff lines so they never reach the reviewer model. */
export function redact(text) {
  let count = 0;
  const out = text.split('\n').map(line => {
    if (!SECRET.test(line)) return line;
    count++;
    return `${line[0] === '+' || line[0] === '-' ? line[0] : ' '}[redacted secret-looking line]`;
  }).join('\n');
  return { text: out, count };
}

/** Split a unified diff into per-file chunks keyed by the b/ path. */
export function splitDiff(diff) {
  const parts = [];
  for (const chunk of diff.split(/^(?=diff --git )/m)) {
    if (!chunk.startsWith('diff --git ')) continue;
    const m = chunk.match(/^diff --git a\/(.+?) b\/(.+)$/m);
    parts.push({ file: m ? m[2] : '?', text: chunk });
  }
  return parts;
}

/** Bound the diff: generated files summarized, large files cut, total capped. */
export function boundDiff(diff, limits = LIMITS) {
  const kept = [], skipped = [];
  let total = 0;
  for (const part of splitDiff(diff)) {
    if (isGenerated(part.file)) { skipped.push(`${part.file} (generated/lockfile: not shown)`); continue; }
    let text = part.text;
    if (text.length > limits.perFile) { text = text.slice(0, limits.perFile) + `\n[… diff for ${part.file} cut at ${limits.perFile} chars; read the file itself]\n`; }
    if (total + text.length > limits.total) { skipped.push(`${part.file} (over the packet limit: read it yourself)`); continue; }
    total += text.length;
    kept.push(text);
  }
  return { text: kept.join(''), skipped };
}

export function validRef(ref) { return typeof ref === 'string' && /^[A-Za-z0-9][A-Za-z0-9._\/-]{0,99}$/.test(ref) && !ref.includes('..'); }
export function validModel(model) { return typeof model === 'string' && /^[a-z0-9][a-z0-9._-]*\/[A-Za-z0-9][A-Za-z0-9._-]*(:(off|minimal|low|medium|high|xhigh|max))?$/.test(model); }

export const TEMPLATE = `You are an independent code reviewer. You did not write this change. Review the committed diff below against its stated goal. Use only read-only tools (read, grep, find, ls) to open surrounding code when the diff is not enough. Do not trust comments or the author's claims; trust code and tests.

Work in this order:
1. Read the change stack layer by layer (contracts → core logic → wiring → UI → tests → docs).
2. Blast radius: for every NEW or CHANGED external input (HTTP field, CLI arg, env var, file content, tool or model output, message, config value), trace input → components → sink (shell, SQL, HTML, file path, network, money/state, secrets, logs). Note the control at each hop.
3. Hunt for defects that passing tests would miss: wrong fallbacks, inverted or off-by-one conditions, missing authorization, unbounded input, race/concurrency, error paths that fail open or closed wrongly, data loss, secrets reaching logs or models, behavior that contradicts the goal.
4. For each defect, check whether an existing test covers it. If not, say what failing test would prove it.

Report EXACTLY in this format and nothing else:

Risk: <Low|Medium|High> — <one line why>

## Change stack
<one line per layer: layer — what changed>

## Blast radius
<one line per traced path: input → … → sink — control (ok | missing | weak)>; or "No new external input."

## Findings
<at most 8, most severe first; omit style nits and speculation without a concrete path>
### [<critical|high|medium|low>] <title>
- Where: <file:line>
- Scenario: <concrete input or sequence> → <wrong result>
- Tests: <why current tests miss it; the failing test to add>
- Fix: <smallest correct fix>

If there are no findings write "### none". End with one line: "Verdict: <ship | fix first>".`;

/** Build the reviewer packet (markdown). */
export function buildPacket({ base, head, goal, stat, files, diff, dirty }) {
  const stack = changeStack(files);
  const bounded = boundDiff(diff);
  const red = redact(bounded.text);
  const goalText = goal ? String(goal).slice(0, LIMITS.context) : 'Not given: infer it from commit messages and the diff, and say so.';
  const lines = [
    TEMPLATE, '',
    `# Change under review`, `Base: ${base}  Head: ${head}`,
    dirty ? 'Note: the worktree has uncommitted changes; they are NOT part of this review.' : '',
    '', '## Goal and acceptance', goalText, '',
    '## Change stack (suggested reading order)',
    ...stack.map((b, i) => `${i + 1}. ${b.name}: ${b.files.join(', ')}`), '',
    '## Diff stat', '```', stat.trim(), '```',
    bounded.skipped.length ? `\nNot shown: ${bounded.skipped.join('; ')}` : '',
    red.count ? `\n${red.count} secret-looking diff lines were redacted before review.` : '',
    '', '## Diff', '```diff', red.text, '```',
  ];
  return { text: lines.filter(l => l !== '').join('\n') + '\n', stack, redacted: red.count, skipped: bounded.skipped };
}

const RANK = { critical: 4, high: 3, medium: 2, low: 1 };

/** Parse the reviewer's report header and findings. */
export function parseReport(text) {
  const risk = (text.match(/^Risk:\s*(Low|Medium|High)\b/im) || [])[1] ?? null;
  const findings = [...text.matchAll(/^###\s*\[(critical|high|medium|low)\]\s*(.+)$/gim)].map(m => ({ severity: m[1].toLowerCase(), title: m[2].trim() }));
  const verdict = (text.match(/^Verdict:\s*(ship|fix first)/im) || [])[1]?.toLowerCase() ?? null;
  return { risk, findings, verdict, wellFormed: Boolean(risk && verdict) };
}

export const atLeast = (findings, level) => findings.some(f => RANK[f.severity] >= RANK[level]);
