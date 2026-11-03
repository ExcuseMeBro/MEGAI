// Loads the real tgrep extension source with minimal Pi API stubs (Node type stripping).
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const source = new URL('../pi-defaults/extensions/tgrep/', import.meta.url);

function stubPackage(root, name, body) {
  const dir = join(root, 'node_modules', ...name.split('/'));
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, 'package.json'), JSON.stringify({ name, type: 'module', main: 'index.js' }));
  writeFileSync(join(dir, 'index.js'), body);
}

async function loadTool(root) {
  mkdirSync(join(root, 'ext'));
  for (const file of ['index.ts', 'search-policy.mjs']) copyFileSync(new URL(file, source), join(root, 'ext', file));
  writeFileSync(join(root, 'package.json'), '{"type":"module"}');
  stubPackage(root, '@earendil-works/pi-ai',
    'const f = (o) => o; export const Type = { Object: f, Optional: f, String: f, Boolean: f, Integer: f };\n');
  stubPackage(root, '@earendil-works/pi-coding-agent',
    'export const defineTool = (t) => t;\nexport const truncateHead = (text) => ({ content: text, truncated: false });\n');
  const mod = await import(pathToFileURL(join(root, 'ext', 'index.ts')));
  let tool, hook;
  mod.default({ on: (_event, handler) => { hook = handler; }, registerTool: (t) => { tool = t; } });
  return { tool, hook };
}

const bashContext = (cwd) => ({
  cwd,
  executeTool: async (_name, { command }) => {
    let text;
    try { text = execFileSync('bash', ['-c', command], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }); }
    catch (error) { text = error.stdout; }
    return { result: { content: [{ type: 'text', text }], details: {} }, isError: false };
  },
});

test('tgrep tool live-scans by default, rejects a missing scope once and registers the grep guard', async () => {
  const root = mkdtempSync(join(tmpdir(), 'megai-tgrep-ext-'));
  try {
    const { tool, hook } = await loadTool(root);
    const scope = join(root, 'scope');
    mkdirSync(join(scope, 'src'), { recursive: true });
    writeFileSync(join(scope, 'src', 'a.ts'), 'export const needleValue = 1;\n');
    const ctx = bashContext(scope);

    const found = await tool.execute('1', { pattern: 'needleValue' }, undefined, undefined, ctx);
    assert.match(found.content[0].text, /src\/a\.ts:1:export const needleValue/);
    assert.match(found.content[0].text, /\[Discovery only:/);
    assert.equal(found.details.indexed, false);

    await assert.rejects(tool.execute('2', { pattern: 'x', path: 'missing/dir' }, undefined, undefined, ctx),
      /tgrep path not found: .*missing\/dir/);

    assert.equal(hook({ toolName: 'bash', input: { command: 'grep -rn foo ~' } })?.block, true);
    assert.equal(hook({ toolName: 'bash', input: { command: 'grep -n foo src/a.ts' } }), undefined);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
