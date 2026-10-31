import { execFile } from 'node:child_process';
import { lstatSync, readdirSync, realpathSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, relative, sep } from 'node:path';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);
export const LIMIT_KIB = 3 * 1024 * 1024; // 3 GiB of allocated disk blocks.
export const RECHECK_MS = 30 * 60 * 1000;
const DU_TIMEOUT_MS = 20_000;

export function projectRoot(cwd) {
  let current = realpathSync(cwd);
  const start = current;
  while (true) {
    try {
      const dotGit = lstatSync(join(current, '.git'));
      if (dotGit.isDirectory() || dotGit.isFile()) return current;
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error;
    }
    const parent = dirname(current);
    if (parent === current) return start; // Non-Git project: measure the selected cwd only.
    current = parent;
  }
}

export async function runDu(args) {
  // du reports allocated blocks, includes ignored build caches, counts hardlinks once,
  // and does not follow child symlinks. No shell, writes, or traversal above the root.
  const { stdout } = await execFileAsync('du', args, {
    encoding: 'utf8', timeout: DU_TIMEOUT_MS, maxBuffer: 512 * 1024,
    env: { PATH: '/usr/bin:/bin', LC_ALL: 'C' }, // No session secrets in the du subprocess.
  });
  return stdout;
}

function parseRows(output, root) {
  const rows = [];
  for (const line of output.split('\n')) {
    const tab = line.indexOf('\t');
    if (tab < 1) continue;
    const size = line.slice(0, tab), path = line.slice(tab + 1);
    if (!/^\d+$/.test(size)) continue;
    if (path !== root && !path.startsWith(root + sep)) continue;
    rows.push({ path, kib: Number(size) });
  }
  return rows;
}

function totalFrom(output, root) {
  const row = parseRows(output, root).find(entry => entry.path === root);
  if (!row || !Number.isSafeInteger(row.kib)) throw new Error('du did not return a valid project total');
  return row.kib;
}

function childrenFrom(output, root) {
  const dirs = parseRows(output, root)
    .filter(entry => entry.path !== root && relative(root, entry.path).split(sep).length === 1 && Number.isSafeInteger(entry.kib))
    .map(entry => ({ ...entry, directory: true }));
  // du -d 1 omits files at the root of each measured directory. Include them
  // from allocated stat blocks so a large archive at the project root is named.
  const files = readdirSync(root, { withFileTypes: true })
    .filter(entry => entry.isFile())
    .map(entry => {
      const path = join(root, entry.name);
      return { path, kib: Math.ceil(lstatSync(path).blocks / 2), directory: false };
    });
  return [...dirs, ...files].sort((a, b) => b.kib - a.kib);
}

export async function measure(root, { run = runDu, details = false } = {}) {
  // The first walk gives both the total and top-level directories; don't scan
  // the whole project twice. Only drill into one directory when details matter.
  const first = await run(['-k', '-d', '1', '--', root]);
  const kib = totalFrom(first, root);
  if (!details && kib <= LIMIT_KIB) return { root, kib, top: [], nested: [] };
  let top = [], nested = [], detailError;
  try {
    top = childrenFrom(first, root);
    const biggestDir = top.find(entry => entry.directory);
    if (biggestDir) {
      nested = childrenFrom(await run(['-k', '-d', '1', '--', biggestDir.path]), biggestDir.path);
    }
  } catch (error) {
    detailError = error;
  }
  return { root, kib, top: top.slice(0, 4), nested: nested.slice(0, 3), detailError };
}

const gb = kib => `${(kib / 1024 / 1024).toFixed(2)} GiB`;
const safe = value => value.replace(/[\x00-\x1f\x7f]/g, '?').slice(0, 140);

export function formatReport(result) {
  const high = result.kib > LIMIT_KIB;
  const lines = [`${high ? '⚠ Loyiha hajmi 3 GiB chegaradan oshdi' : 'Loyiha disk hajmi'}: ${gb(result.kib)} (chegara: 3 GiB)`, `Loyiha: ${safe(result.root)}`];
  for (const entry of result.top) lines.push(`  ${gb(entry.kib)}  ${safe(relative(result.root, entry.path))}${entry.directory ? '/' : ''}`);
  for (const entry of result.nested) lines.push(`    ${gb(entry.kib)}  ${safe(relative(result.root, entry.path))}${entry.directory ? '/' : ''}`);
  if (result.detailError) lines.push(`Sabablar to‘liq aniqlanmadi: ${safe(String(result.detailError.message ?? result.detailError))}`);
  else if (high && !result.top.length) lines.push('Katta hajm loyihaning ildizidagi fayllarda yoki ajratilmagan kataloglarda.');
  lines.push('Bu ogohlantirish xolos; hech narsa avtomatik o‘chirilmaydi. /project-size — qayta tekshirish.');
  return lines.join('\n');
}

export function createMonitor({ getRoot = projectRoot, scan = measure, now = Date.now, emit, interval = RECHECK_MS } = {}) {
  let lastCheck = -Infinity, warnedRoot, warnedKiB = 0, closed = false, pending;
  async function check(cwd, manual = false) {
    if (closed) return;
    if (pending) {
      await pending;
      if (manual) return check(cwd, true); // An explicit command must still show a report.
      return;
    } // Only one filesystem walk per Pi session at a time.
    if (!manual && now() - lastCheck < interval) return;
    lastCheck = now();
    pending = Promise.resolve().then(async () => {
      try {
        const root = getRoot(cwd);
        if (!manual && root === homedir()) return; // $HOME is not itself a project.
        const result = await scan(root, { details: manual });
        if (closed) return;
        const high = result.kib > LIMIT_KIB;
        const changed = warnedRoot !== root || result.kib > warnedKiB * 1.1;
        if (manual || (high && changed)) emit(formatReport(result), high ? 'warning' : 'info');
        if (high) { warnedRoot = root; warnedKiB = result.kib; }
        else { warnedRoot = undefined; warnedKiB = 0; }
      } catch (error) {
        if (!closed) emit(`Loyiha hajmini tekshirib bo‘lmadi: ${safe(String(error.message ?? error))}. /project-size bilan qayta urinib ko‘ring.`, 'warning');
      }
    }).finally(() => { pending = undefined; });
    return pending;
  }
  return {
    startup: cwd => { void check(cwd); }, // Scan async; do not stall session startup or a model turn.
    settled: cwd => { void check(cwd); },
    manual: cwd => check(cwd, true),
    shutdown: () => { closed = true; },
  };
}
