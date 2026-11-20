export const MARKER = 'Factory-Flow: ';
export const SHA = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
const ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const KEY = /^[a-z0-9][a-z0-9_-]{0,39}$/;
const ACTIVE = new Set(['todo', 'doing']);
const SATISFIED = new Set(['review', 'done']);
const TYPES = new Set(['decision', 'access', 'spec', 'resource', 'check']);
const STAGES = new Set(['candidate', 'remote-verified']);
const GATES = new Set(['pass', 'fail', 'wait']);
const unsafe = /[\p{Cc}\p{Cf}\u2028\u2029]/u;
const object = value => !!value && typeof value === 'object' && !Array.isArray(value);
const isText = (value, max = 320) => typeof value === 'string' && !!value.trim() && value.length <= max && !unsafe.test(value);
const isNumber = (value, max) => Number.isSafeInteger(value) && value >= 0 && value <= max;
const isSha = value => typeof value === 'string' && SHA.test(value);
export const isProject = value => typeof value === 'string' && ID.test(value) && value !== 'all';
export const isActive = task => !task.human && ACTIVE.has(task.status);
export const isHumanWait = wait => ['decision', 'access', 'spec'].includes(wait.type);

export class FlowError extends Error {}
const need = (condition, message) => { if (!condition) throw new FlowError(message); };

export function taskNumber(ref, project) {
  const match = typeof ref === 'string' && /^([a-z0-9][a-z0-9_-]{0,63})#([1-9][0-9]{0,15})$/.exec(ref);
  need(match && match[1] === project && Number.isSafeInteger(Number(match[2])), 'Expected a task ID in the bound Brokan project.');
  return Number(match[2]);
}

export function task(value, project, id) {
  need(object(value) && value.project === project && isNumber(value.id, Number.MAX_SAFE_INTEGER) && value.id > 0 &&
    (id === undefined || value.id === id) && typeof value.status === 'string' && KEY.test(value.status) &&
    typeof value.human === 'boolean' && typeof value.description === 'string' && value.description.length <= 128_000 &&
    isNumber(value.comments, 100_000) && isText(value.updated_at, 64), 'Invalid or mismatched Brokan task.');
  return value;
}

export function dependencies(description, project) {
  const lines = description.split(/\r?\n/).filter(line => /^Factory depends-on:/i.test(line));
  if (!lines.length) return [];
  need(lines.length === 1 && lines[0].length <= 1024, 'Invalid Factory dependency declaration.');
  const refs = lines[0].slice('Factory depends-on:'.length).trim().split(/\s+/);
  need(refs.length <= 12, 'Too many Factory dependencies on one task.');
  const ids = refs.map(ref => taskNumber(ref, project));
  need(new Set(ids).size === ids.length, 'Duplicate Factory dependencies.');
  return ids;
}

function delivery(value) {
  need(isSha(value.sha) && STAGES.has(value.stage) && Array.isArray(value.checks) && value.checks.length > 0 && value.checks.length <= 12,
    'Invalid candidate receipt.');
  const ids = new Set();
  for (const check of value.checks) {
    need(object(check) && typeof check.name === 'string' && KEY.test(check.name) && GATES.has(check.status) && !ids.has(check.name), 'Invalid receipt check.');
    ids.add(check.name);
  }
  if (value.stage === 'remote-verified') {
    need(typeof value.remote === 'string' && /^(?!\.)(?!.*(?:\.\.|\/\.|\.lock(?:\/|$)))[a-zA-Z0-9_-][a-zA-Z0-9_./-]{0,95}$/.test(value.remote) &&
      !value.remote.endsWith('/') && !value.remote.endsWith('.') && !value.remote.includes('//') &&
      isSha(value.remoteHead) && value.remoteHead.length === value.sha.length && value.checks.every(check => check.status === 'pass'), 'Invalid remote attestation; all required checks must pass.');
  } else {
    need(value.remote === undefined && value.remoteHead === undefined, 'Candidate receipts cannot claim remote verification.');
  }
  return value;
}

export function records(comments, id) {
  need(Array.isArray(comments) && comments.length <= 2000, 'Brokan comments unavailable or too numerous.');
  const active = new Map(), answered = new Map(), seen = new Set(), receipts = new Map();
  const ids = new Set();
  for (const comment of comments) {
    need(object(comment) && comment.task_id === id && isNumber(comment.id, Number.MAX_SAFE_INTEGER) &&
      comment.id > 0 && !ids.has(comment.id) && typeof comment.body === 'string', 'Invalid or mismatched Brokan comment.');
    ids.add(comment.id);
  }
  for (const { body } of [...comments].sort((a, b) => a.id - b.id)) {
    if (!body.startsWith(MARKER)) continue;
    need(body.length <= 8192 && !/[\r\n]/.test(body), 'Invalid Factory record; use a single line.');
    let value;
    try { value = JSON.parse(body.slice(MARKER.length)); }
    catch { throw new FlowError('Invalid Factory record JSON.'); }
    need(object(value) && value.v === 1, 'Unsupported Factory record.');
    if (value.kind === 'receipt') {
      const record = delivery(value);
      receipts.set(record.sha, record);
      continue;
    }
    need(typeof value.key === 'string' && KEY.test(value.key), 'Invalid Factory question key.');
    if (value.kind === 'wait') {
      need(!seen.has(value.key) && TYPES.has(value.type) && ['blocked', 'question', 'recommendation', 'next'].every(key => isText(value[key])), 'Invalid or duplicate Factory question.');
      seen.add(value.key);
      active.set(value.key, value);
    } else if (value.kind === 'answer') {
      need(active.has(value.key) && isText(value.answer), 'Factory answer has no open question.');
      answered.set(value.key, { wait: active.get(value.key), answer: value.answer });
      active.delete(value.key);
    } else {
      throw new FlowError('Unknown Factory record kind.');
    }
  }
  return { active, answered, receipts };
}

export function readiness(root, tasks, waits) {
  const done = new Set(), visiting = new Set();
  const blockers = new Set();
  const visit = id => {
    const ref = `${root.project}#${id}`;
    if (visiting.has(id)) { blockers.add(`cycle at ${ref}`); return; }
    if (done.has(id)) return;
    const item = tasks.get(id);
    if (!item) { blockers.add(`unknown ${ref}`); return; }
    if (done.size + visiting.size >= 160) { blockers.add('dependency graph limit'); return; }
    if (id !== root.id && !SATISFIED.has(item.status)) blockers.add(`${ref} ${item.status}`);
    visiting.add(id);
    let children;
    try { children = dependencies(item.description, root.project); }
    catch (err) { if (!(err instanceof FlowError)) throw err; blockers.add(`invalid dependency on ${ref}`); }
    for (const child of children ?? []) visit(child);
    visiting.delete(id);
    done.add(id);
  };
  visit(root.id);
  if (!isActive(root)) blockers.add('not an agent-owned todo/doing candidate');
  if (waits === null) blockers.add('Factory records not verified');
  else for (const wait of waits.active.values()) blockers.add(`${isHumanWait(wait) ? 'needs decision' : 'waiting for resource/check'}: ${wait.key}`);
  return [...blockers];
}

export function requiredChecks(description) {
  const lines = description.split(/\r?\n/).filter(line => /^Factory required-checks:/i.test(line));
  if (!lines.length) return [];
  need(lines.length === 1 && lines[0].length <= 520, 'Invalid Factory check declaration.');
  const names = lines[0].slice('Factory required-checks:'.length).trim().split(/\s+/);
  need(names.length <= 12 && names.every(name => KEY.test(name)) && new Set(names).size === names.length,
    'Invalid or duplicate required Factory checks.');
  return names;
}

export function formatReceipt(state, sha, required) {
  need(isSha(sha), 'Use a full lowercase Git SHA.');
  const item = state.receipts.get(sha);
  if (!item) return [`${sha} — no receipt for this exact SHA; do not reuse earlier checks.`];
  const grouped = status => item.checks.filter(check => check.status === status).map(check => check.name).join(', ') || '—';
  const present = new Set(item.checks.map(check => check.name));
  const missing = required.filter(name => !present.has(name));
  const covered = required.length > 0 && missing.length === 0;
  const remote = item.stage === 'remote-verified' && covered
    ? `Remote attestation (not re-fetched): ${item.remote} @ ${item.remoteHead}`
    : 'Remote: not attested for all required checks.';
  return [`${sha} | passed: ${grouped('pass')} | failed: ${grouped('fail')} | pending: ${grouped('wait')}`,
    !required.length ? 'Required checks not declared.' : missing.length ? `Required checks missing: ${missing.join(', ')}` : 'All declared checks recorded.', remote];
}

const median = values => {
  const sorted = [...values].sort((a, b) => a - b), at = sorted.length >> 1;
  return (sorted.length % 2 ? sorted[at] : (sorted[at - 1] + sorted[at]) / 2);
};

export function evalSummary(input) {
  need(object(input) && input.v === 1 && Array.isArray(input.arms) && input.arms.length === 2 &&
    input.arms.every(arm => typeof arm === 'string' && KEY.test(arm)) && input.arms[0] !== input.arms[1] &&
    Array.isArray(input.cases) && input.cases.length > 0 && input.cases.length <= 200, 'Expected a paired eval with two distinct arms and 1–200 cases.');
  const ids = new Set(), pairs = [];
  for (const item of input.cases) {
    need(object(item) && typeof item.id === 'string' && KEY.test(item.id) && !ids.has(item.id) &&
      Array.isArray(item.runs) && item.runs.length === 2 && item.runs.every(object), 'Invalid or duplicate eval case.');
    ids.add(item.id);
    const runs = input.arms.map(arm => item.runs.find(run => run.arm === arm));
    need(runs.every(run => run && isSha(run.base) && [run.fixture, run.setup].every(value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)) &&
      typeof run.accepted === 'boolean' && isNumber(run.regressions, 10_000) && isNumber(run.ms, 86_400_000) && run.ms > 0 &&
      (run.usdMicros === null || isNumber(run.usdMicros, 1_000_000_000))), 'Incomplete or invalid eval observations.');
    need(runs[0].base === runs[1].base && runs[0].fixture === runs[1].fixture && runs[0].setup === runs[1].setup, 'Eval case inputs or common setup differ between arms.');
    pairs.push(runs);
  }
  const completeCosts = pairs.filter(pair => pair.every(run => run.usdMicros !== null));
  const summary = input.arms.map((arm, i) => {
    const runs = pairs.map(pair => pair[i]);
    return { arm, accepted: runs.filter(run => run.accepted && run.regressions === 0).length,
      regressions: runs.reduce((n, run) => n + run.regressions, 0), medianMs: median(runs.map(run => run.ms)),
      faster: pairs.filter(pair => pair[i].ms < pair[1-i].ms).length,
      medianUsdMicros: completeCosts.length ? median(completeCosts.map(pair => pair[i].usdMicros)) : null };
  });
  return { pairs: pairs.length, costPairs: completeCosts.length, summary };
}
