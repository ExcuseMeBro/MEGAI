import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, symlinkSync, rmSync, realpathSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import {
  LIMIT_KIB, RECHECK_MS, projectRoot, measure, formatReport, createMonitor,
} from '../pi-defaults/extensions/megai-project-size/measure.mjs';

async function fixture(fn) {
  const base = mkdtempSync(join(tmpdir(), 'pi-project-size-'));
  try { return await fn(base); } finally { rmSync(base, { recursive: true, force: true }); }
}
const tick = () => new Promise(resolve => setImmediate(resolve));

test('actual Pi extension registers startup/settled hooks and manual command without changing project', async () => fixture(async base => {
  const { default: extension } = await import(new URL('../pi-defaults/extensions/megai-project-size/index.ts', import.meta.url));
  const hooks = new Map(), commands = new Map(), alerts = [];
  extension({ on: (name, handler) => hooks.set(name, handler),
    registerCommand: (name, command) => commands.set(name, command) });
  const ctx = { cwd: base, hasUI: true, ui: { notify: (message, type) => alerts.push({ message, type }) } };
  await hooks.get('session_start')({}, ctx);
  await commands.get('project-size').handler('', ctx);
  assert.equal(alerts.length, 1);
  assert.match(alerts[0].message, /Loyiha disk hajmi/);
  assert.equal(alerts[0].type, 'info');
  await hooks.get('agent_settled')({}, ctx);
  assert.equal(alerts.length, 1);
  await hooks.get('session_shutdown')({}, ctx);
}));

test('nearest Git repository/worktree root, non-Git cwd and symlinks are bounded', () => fixture(base => {
  const repo = join(base, 'repo'), nested = join(repo, 'src', 'deep');
  mkdirSync(nested, { recursive: true });
  writeFileSync(join(repo, '.git'), 'gitdir: /elsewhere'); // Worktree file, not directory.
  assert.equal(projectRoot(nested), realpathSync(repo));
  mkdirSync(join(nested, '.git'));
  assert.equal(projectRoot(nested), realpathSync(nested)); // Nested repository takes precedence.
  const plain = join(base, 'notgit'); mkdirSync(plain);
  assert.equal(projectRoot(plain), realpathSync(plain));
  symlinkSync(repo, join(base, 'link'));
  assert.equal(projectRoot(join(base, 'link', 'src')), realpathSync(repo));
}));

test('real du counts ignored caches and large root files, not linked external content', async () => {
  const base = mkdtempSync(join(tmpdir(), 'pi-project-size-'));
  const outside = mkdtempSync(join(tmpdir(), 'pi-project-size-external-'));
  try {
    mkdirSync(join(base, 'node_modules'));
    writeFileSync(join(base, 'node_modules', 'cache.bin'), Buffer.alloc(32768));
    writeFileSync(join(base, 'archive.zip'), Buffer.alloc(65536));
    writeFileSync(join(outside, 'huge.bin'), Buffer.alloc(1024 * 1024));
    symlinkSync(outside, join(base, 'external'));
    const result = await measure(base, { details: true });
    assert.ok(result.kib > 0 && result.kib < 512);
    assert.ok(result.top.some(entry => entry.path === join(base, 'archive.zip') && !entry.directory));
    assert.ok(result.top.some(entry => entry.path === join(base, 'node_modules') && entry.directory));
    assert.ok(!result.top.some(entry => entry.path.includes('huge.bin')));
    assert.match(formatReport(result), /archive\.zip/);
    assert.match(formatReport(result), /node_modules\//);
  } finally {
    rmSync(base, { recursive: true, force: true });
    rmSync(outside, { recursive: true, force: true });
  }
});

test('over 3 GiB provides concrete causes, directory breakdown and never deletes', async () => fixture(async base => {
  const cache = join(base, '.dart_tool'); mkdirSync(cache);
  const rootKiB = LIMIT_KIB + 1024;
  const run = async args => {
    if (args.at(-1) === base) return `${LIMIT_KIB}\t${cache}\n${rootKiB}\t${base}\n`;
    return `1048576\t${join(cache, 'build')}\n${LIMIT_KIB}\t${cache}\n`;
  };
  const result = await measure(base, { run });
  const report = formatReport(result);
  assert.match(report, /3 GiB chegaradan oshdi/);
  assert.match(report, /\.dart_tool\//);
  assert.match(report, /\.dart_tool\/build\//);
  assert.match(report, /hech narsa avtomatik o‘chirilmaydi/);
  assert.equal(result.kib, rootKiB);
}));

test('quiet below threshold, throttled rechecks, changed size alerts and manual always reports', async () => {
  const alerts = []; let time = 0, size = LIMIT_KIB - 1, calls = 0;
  const monitor = createMonitor({ getRoot: () => '/test/project', now: () => time,
    scan: async (root) => { calls++; return { root, kib: size, top: [], nested: [] }; },
    emit: (message, type) => alerts.push({ message, type }), });
  monitor.startup('/test/project'); await tick();
  assert.equal(calls, 1); assert.equal(alerts.length, 0);
  size = LIMIT_KIB + 1; monitor.settled('/test/project'); await tick();
  assert.equal(calls, 1);
  time += RECHECK_MS; monitor.settled('/test/project'); await tick();
  assert.equal(alerts.length, 1); assert.equal(alerts[0].type, 'warning');
  time += RECHECK_MS; monitor.settled('/test/project'); await tick();
  assert.equal(alerts.length, 1); // no duplicate unchanged-size warning
  size *= 1.2; time += RECHECK_MS; monitor.settled('/test/project'); await tick();
  assert.equal(alerts.length, 2);
  size = 1; await monitor.manual('/test/project');
  assert.equal(alerts.at(-1).type, 'info');
  assert.match(alerts.at(-1).message, /Loyiha disk hajmi/);
  monitor.shutdown(); time += RECHECK_MS;
  monitor.settled('/test/project'); await tick(); assert.equal(calls, 5);
});

test('failures are warnings instead of false safe reports; startup skips bare HOME', async () => {
  const alerts = [], monitor = createMonitor({ getRoot: () => homedir(),
    emit: (message, type) => alerts.push({ message, type }),
    scan: async () => { throw Error('du timed out or permission denied'); }, });
  monitor.startup(homedir()); await tick(); assert.equal(alerts.length, 0);
  await monitor.manual(homedir());
  assert.match(alerts[0].message, /du timed out or permission denied/);
  assert.equal(alerts[0].type, 'warning');
});

test('failed detail scan retains measured over-limit alert with explicit uncertainty', async () => fixture(async base => {
  const run = async args => {
    if (args.at(-1) === base) return `${LIMIT_KIB}\t${join(base, 'cache')}\n${LIMIT_KIB + 1}\t${base}\n`;
    throw Error('du breakdown timed out');
  };
  const result = await measure(base, { run });
  assert.match(formatReport(result), /3 GiB chegaradan oshdi/);
  assert.match(formatReport(result), /Sabablar to‘liq aniqlanmadi: du breakdown timed out/);
}));
