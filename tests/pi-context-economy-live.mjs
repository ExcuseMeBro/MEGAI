#!/usr/bin/env node
// Explicit offline scenario; character counts are proxies, not billed tokens.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT && process.env.LAYA_PYTHON);
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const dir = mkdtempSync(join(tmpdir(), 'pi-context-economy-'));
const project = join(dir, 'project');
const agent = join(dir, 'agent'), extension = join(agent, 'extensions/megai-laya');
mkdirSync(project); mkdirSync(extension, { recursive: true });
for (const name of ['index.ts', 'bridge.py', 'compaction.ts'])
  copyFileSync(resolve('pi-skill/laya', name), join(extension, name));
const modules = ['payments', 'retry', 'calendar', 'cache', 'users', 'theme'];
const symbols = ['processPayment', 'retryPayment', 'renderCalendar', 'readCache', 'findUser', 'renderTheme'];
const bodies = modules.map((name, i) => {
  const body = `// ${name} implementation fixture\nexport function ${symbols[i]}(value) {\n  return value;\n}\n`;
  return body + Array.from({ length: 80 }, (_, n) => `// ${name} unrelated implementation detail ${n}\n`).join('');
});
modules.forEach((name, i) => writeFileSync(join(project, `${name}.ts`), bodies[i]));
execFileSync('git', ['init', '-q', project]);
let loaded;
try {
  const codedbEnv = { ...process.env, CODEDB_NO_TELEMETRY: '1' };
  const wrapper = resolve('pi-skill/extensions/codedb.sh');
  const before = performance.now();
  const find = execFileSync('bash', [wrapper, 'find', 'processPayment'],
    { cwd: project, env: codedbEnv, encoding: 'utf8', timeout: 30_000 });
  assert.match(find, /payments\.ts/);
  const outline = execFileSync('bash', [wrapper, 'outline', 'payments.ts'],
    { cwd: project, env: codedbEnv, encoding: 'utf8', timeout: 30_000 });
  assert.match(outline, /processPayment/);
  // This named-symbol question requires the exact function range, not all files.
  const exact = readFileSync(join(project, 'payments.ts'), 'utf8').split('\n').slice(0, 4).join('\n');
  const discoveryMs = performance.now() - before;
  const allChars = bodies.join('\n').length;
  const selectedChars = find.length + outline.length + exact.length;
  assert.ok(selectedChars < allChars, 'bounded structural lookup should expose less fixture text');
  delete process.env.LAYA_BRIDGE_TEST;
  process.env.HF_HUB_OFFLINE = '1';
  const loader = new DefaultResourceLoader({ cwd: project, agentDir: agent });
  await loader.reload();
  loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const tools = new Map(loaded.extensions.flatMap(e => [...e.tools].map(([n, t]) => [n, t.definition])));
  const paths = modules.map(name => `${name}.ts`);
  writeFileSync(join(project, 'oversized.txt'), 'x'.repeat(20_001));
  const rankingStart = performance.now();
  const raw = await tools.get('sift').execute('rank',
    { query: 'Which files implement payment retry behavior?', paths: [...paths, 'oversized.txt'] },
    undefined, undefined, { cwd: project });
  const rankingMs = performance.now() - rankingStart;
  const result = JSON.parse(raw.content[0].text);
  assert.equal(result.ok, true);
  assert.deepEqual(result.files.map(f => f.path), [...paths, 'oversized.txt']);
  for (const f of result.files.slice(0, paths.length))
    assert.ok(Number.isFinite(f.probability), JSON.stringify(f));
  assert.ok(result.files.at(-1).error, 'unscored file must remain an explicit unresolved result');
  assert.ok(!raw.content[0].text.includes('unrelated implementation detail'), 'full source stays local');
  // Ranking is advisory. No threshold is used to delete candidates or claim coverage.
  console.log(JSON.stringify({ fixture: 'synthetic six-module project',
    codedb: { allFilesChars: allChars, selectedContextChars: selectedChars, elapsedMs: Math.round(discoveryMs) },
    sift: { candidateChars: allChars, resultChars: raw.content[0].text.length,
      elapsedMs: Math.round(rankingMs), files: result.files },
    units: 'characters and elapsed milliseconds; not measured tokens or cost',
    inference: 'real offline Laya, no stub; no ranking-based exclusion' }, null, 2));
} finally {
  for (const fn of loaded?.extensions.flatMap(e => e.handlers.get('session_shutdown') ?? []) ?? []) await fn({}, {});
  rmSync(dir, { recursive: true, force: true }); // only this freshly-created disposable fixture
}
