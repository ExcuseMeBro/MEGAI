// The `antigravity` tool: one self-contained prompt goes to the Antigravity CLI in
// headless print mode and its answer comes back. Offline — a fake `agy` on the
// configured bin path records argv and prints a canned answer; no provider, no network.
import assert from 'node:assert/strict';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-antigravity-'));
process.env.PI_OFFLINE = '1';
try {
  const binDir = join(temp, 'bin');
  mkdirSync(binDir, { recursive: true });
  const argvFile = join(temp, 'argv.json');
  const fake = join(binDir, 'agy');
  // Records the argv it received and answers with AGY_ANSWER (empty = real failure).
  writeFileSync(fake, `#!/usr/bin/env node
const { writeFileSync } = require('node:fs');
writeFileSync(process.env.AGY_ARGV_FILE, JSON.stringify(process.argv.slice(2)));
process.stdout.write(process.env.AGY_ANSWER ?? '');
`);
  chmodSync(fake, 0o755);
  process.env.MEGAI_AGY_BIN = fake;
  process.env.AGY_ARGV_FILE = argvFile;

  const loader = new DefaultResourceLoader({
    cwd: temp, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [resolve('pi-skill/antigravity/index.ts')],
  });
  await loader.reload();
  assert.deepEqual(loader.getExtensions().errors, []);
  const tools = new Map();
  for (const extension of loader.getExtensions().extensions)
    for (const [name, tool] of extension.tools) tools.set(name, tool.definition);
  const tool = tools.get('antigravity');
  assert.ok(tool, 'the extension must register the antigravity tool');
  assert.ok(tool.parameters, 'the tool must declare parameters');

  const work = join(temp, 'work');
  mkdirSync(work, { recursive: true });
  writeFileSync(join(work, 'note.md'), 'needle-alpha\n');
  writeFileSync(join(work, 'huge.log'), 'x'.repeat(600 * 1024));
  writeFileSync(join(work, '.env'), 'TOKEN=secret\n');
  writeFileSync(join(work, 'binary.bin'), Buffer.from([0, 1, 2]));
  writeFileSync(join(temp, 'outside.txt'), 'outside-value\n');
  const ctx = { hasUI: false, mode: 'print', cwd: work, isIdle: () => true,
    isProjectTrusted: () => false, abort() {}, getSystemPrompt: () => '', ui: { notify() {} } };
  const run = (params) => tool.execute('antigravity', params, undefined, undefined, ctx);
  const argv = () => JSON.parse(readFileSync(argvFile, 'utf8'));

  // A normal question: the file is inlined into the prompt and the model is passed.
  process.env.AGY_ANSWER = 'ANTIGRAVITY_ANSWER';
  const ok = await run({ prompt: 'Summarize the note', files: ['note.md'], model: 'gemini-3.1-pro-high' });
  assert.equal(ok.content[0].text, 'ANTIGRAVITY_ANSWER');
  const sent = argv();
  assert.equal(sent[0], '-p');
  assert.match(sent[1], /Summarize the note/);
  assert.match(sent[1], /needle-alpha/, 'the requested file must be inlined into the prompt');
  assert.deepEqual(sent.slice(2, 4), ['--print-timeout', '300s']);
  assert.equal(sent[sent.indexOf('--model') + 1], 'gemini-3.1-pro-high');
  assert.ok(!sent.join(' ').includes('dangerously'), 'headless runs must never auto-approve permissions');
  assert.deepEqual(ok.details.notes, [], 'a clean run reports no notes');

  // Unsafe, binary, escaping and over-cap paths are refused without failing the turn.
  const capped = await run({ prompt: 'Read the log', files: ['huge.log', 'missing.md', '.env', '../outside.txt', 'binary.bin'] });
  assert.equal(capped.content[0].text, 'ANTIGRAVITY_ANSWER');
  assert.equal(capped.details.notes.length, 5, 'every refused or unreadable file is reported');
  assert.match(capped.details.notes[0], /per-file cap/);
  assert.match(capped.details.notes[2], /credential-like/);
  assert.match(capped.details.notes[3], /outside the working directory/);
  assert.match(capped.details.notes[4], /binary content/);
  assert.ok(!argv().includes('--model'), 'an omitted model is left to the CLI default');
  assert.ok(!argv()[1].includes('TOKEN=secret'), 'credential-like file contents must not leave the process');
  assert.ok(!argv()[1].includes('outside-value'), 'outside file contents must not leave the process');

  // The CLI's auto-denied permission turn is reported as unusable, not as an answer.
  process.env.AGY_ANSWER = 'jetski: no output produced — a tool required the "command" permission that headless mode cannot prompt for';
  const denied = await run({ prompt: 'Read the repo' });
  assert.match(denied.content[0].text, /not usable evidence/);
  assert.match(denied.content[0].text, /files/);

  // An empty turn is a failure, not an empty answer.
  process.env.AGY_ANSWER = '';
  const empty = await run({ prompt: 'Say nothing' });
  assert.match(empty.content[0].text, /produced no output/);

  console.log('pi-antigravity: PASS');
} finally {
  rmSync(temp, { recursive: true, force: true });
}
