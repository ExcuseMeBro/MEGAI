// The `antigravity` tool: one self-contained prompt goes to the Antigravity CLI in
// headless print mode and its answer comes back. Offline — a fake `agy` on the
// configured bin path records argv and prints a canned answer; no provider, no network.
import assert from 'node:assert/strict';
import { chmodSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
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
const { join } = require('node:path');
writeFileSync(process.env.AGY_ARGV_FILE, JSON.stringify(process.argv.slice(2)));
if (process.env.AGY_WRITE_REL) writeFileSync(join(process.cwd(), process.env.AGY_WRITE_REL), 'delegated\\n');
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
  const delegate = tools.get('antigravity_delegate');
  assert.ok(tool, 'the extension must register the antigravity tool');
  assert.ok(tool.parameters, 'the tool must declare parameters');
  assert.ok(delegate, 'the extension must register the delegated worker tool');

  const work = join(temp, 'work');
  mkdirSync(work, { recursive: true });
  writeFileSync(join(work, 'note.md'), 'needle-alpha\n');
  writeFileSync(join(work, 'huge.log'), 'x'.repeat(600 * 1024));
  writeFileSync(join(work, '.env'), 'TOKEN=secret\n');
  writeFileSync(join(work, 'binary.bin'), Buffer.from([1, 2, 3]));
  writeFileSync(join(work, 'invalid.bin'), Buffer.from([0xc3, 0x28]));
  writeFileSync(join(work, 'del.bin'), Buffer.from([0x7f]));
  writeFileSync(join(work, 'c1.bin'), Buffer.from([0xc2, 0x80]));
  symlinkSync('.env', join(work, 'safe.txt'));
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
  assert.equal(sent[sent.indexOf('--mode') + 1], 'plan');
  assert.ok(sent.includes('--sandbox'), 'headless runs must stay sandboxed');
  assert.equal(sent[sent.indexOf('--print-timeout') + 1], '300s');
  assert.equal(sent[sent.indexOf('--model') + 1], 'gemini-3.1-pro-high');
  assert.ok(!sent.join(' ').includes('dangerously'), 'headless runs must never auto-approve permissions');
  assert.deepEqual(ok.details.notes, [], 'a clean run reports no notes');

  // Unsafe, binary, escaping and over-cap paths are refused without failing the turn.
  const capped = await run({ prompt: 'Read the log',
    files: ['huge.log', 'missing.md', '.env', '../outside.txt', 'binary.bin', 'safe.txt', 'invalid.bin', 'del.bin', 'c1.bin'] });
  assert.equal(capped.content[0].text, 'ANTIGRAVITY_ANSWER');
  assert.equal(capped.details.notes.length, 9, 'every refused or unreadable file is reported');
  assert.match(capped.details.notes[0], /per-file cap/);
  assert.match(capped.details.notes[2], /credential-like/);
  assert.match(capped.details.notes[3], /outside the working directory/);
  assert.match(capped.details.notes[4], /binary content/);
  assert.match(capped.details.notes[5], /credential-like/, 'resolved symlink target names are screened');
  assert.match(capped.details.notes[6], /binary content/, 'invalid UTF-8 is refused');
  assert.match(capped.details.notes[7], /binary content/, 'ASCII DEL is refused');
  assert.match(capped.details.notes[8], /binary content/, 'UTF-8 C1 controls are refused');
  assert.ok(!argv().includes('--model'), 'an omitted model is left to the CLI default');
  assert.ok(!argv()[1].includes('TOKEN=secret'), 'credential-like file contents must not leave the process');
  assert.ok(!argv()[1].includes('outside-value'), 'outside file contents must not leave the process');

  // Model ids are values, never another CLI option; rejection happens before spawn.
  const beforeInvalid = readFileSync(argvFile, 'utf8');
  const invalidModel = await run({ prompt: 'x', model: '--dangerously-skip-permissions' });
  assert.match(invalidModel.content[0].text, /invalid model/i);
  assert.equal(readFileSync(argvFile, 'utf8'), beforeInvalid, 'invalid model ids must not execute agy');

  // Ordinary answers about permissions remain valid.
  process.env.AGY_ANSWER = 'Unix permission bits are 0644';
  const ordinary = await run({ prompt: 'Explain Unix permissions' });
  assert.equal(ordinary.content[0].text, 'Unix permission bits are 0644');

  // The CLI's auto-denied permission turn is reported as unusable, not as an answer.
  process.env.AGY_ANSWER = 'jetski: no output produced — a tool required the "command" permission that headless mode cannot prompt for';
  const denied = await run({ prompt: 'Read the repo' });
  assert.match(denied.content[0].text, /not usable evidence/);
  assert.match(denied.content[0].text, /files/);

  // An empty turn is a failure, not an empty answer.
  process.env.AGY_ANSWER = '';
  const empty = await run({ prompt: 'Say nothing' });
  assert.match(empty.content[0].text, /produced no output/);

  // Delegated implementation is allowed only in a clean linked worktree and uses accept-edits+sandbox.
  const repo = join(temp, 'repo');
  const linked = join(temp, 'repo-task');
  mkdirSync(repo, { recursive: true });
  execFileSync('git', ['init', '-b', 'feature-base', repo], { stdio: 'ignore' });
  execFileSync('git', ['-C', repo, 'config', 'user.email', 'test@example.com']);
  execFileSync('git', ['-C', repo, 'config', 'user.name', 'Pi Test']);
  writeFileSync(join(repo, 'README.md'), 'baseline\n');
  execFileSync('git', ['-C', repo, 'add', 'README.md']);
  execFileSync('git', ['-C', repo, 'commit', '-m', 'baseline'], { stdio: 'ignore' });
  execFileSync('git', ['-C', repo, 'worktree', 'add', '-b', 'task/agy-worker', linked, 'HEAD'], { stdio: 'ignore' });
  const delegateCtx = { ...ctx, cwd: repo };
  const runDelegate = (params) => delegate.execute('antigravity_delegate', params, undefined, undefined, delegateCtx);
  process.env.AGY_ANSWER = 'DELEGATED_ANSWER';
  process.env.AGY_WRITE_REL = 'delegated.txt';
  const delegated = await runDelegate({ task: 'Add the smallest focused change and report tests.', worktree: linked, model: 'gemini-3.1-pro-high', timeout_s: 42 });
  assert.match(delegated.content[0].text, /DELEGATED_ANSWER/);
  assert.ok(existsSync(join(linked, 'delegated.txt')), 'Agy must run with the linked worktree as cwd');
  const delegatedArgv = argv();
  assert.equal(delegatedArgv[delegatedArgv.indexOf('--mode') + 1], 'accept-edits');
  assert.ok(delegatedArgv.includes('--sandbox'));
  assert.equal(delegatedArgv[delegatedArgv.indexOf('--print-timeout') + 1], '42s');
  assert.ok(!delegatedArgv.join(' ').includes('dangerously'));
  delete process.env.AGY_WRITE_REL;
  rmSync(join(linked, 'delegated.txt'));
  writeFileSync(join(repo, '.git', 'info', 'exclude'), '.env\n*.pem\n*link\n');
  writeFileSync(join(linked, '.env'), 'SECRET=do-not-send\n');
  const ignoredEnv = await runDelegate({ task: 'x', worktree: linked });
  assert.match(ignoredEnv.content[0].text, /credential-like path/i);
  rmSync(join(linked, '.env'));

  writeFileSync(join(linked, 'quoted\t.pem'), 'PRIVATE KEY\n');
  const quotedCredential = await runDelegate({ task: 'x', worktree: linked });
  assert.match(quotedCredential.content[0].text, /credential-like path/i, 'quoted credential filenames must be screened');
  rmSync(join(linked, 'quoted\t.pem'));

  writeFileSync(join(linked, '.env'), 'SECRET=do-not-send\n');
  symlinkSync('.env', join(linked, 'unicode-é\tlink'));
  const symlinkCredential = await runDelegate({ task: 'x', worktree: linked });
  assert.match(symlinkCredential.content[0].text, /credential-like path/i, 'unicode symlink targets must be screened');
  rmSync(join(linked, 'unicode-é\tlink'));
  rmSync(join(linked, '.env'));

  // A caller inside a linked worktree must not be able to pass Git's actual primary checkout.
  const linkedCtx = { ...ctx, cwd: linked };
  const runFromLinked = (params) => delegate.execute('antigravity_delegate', params, undefined, undefined, linkedCtx);
  const refused = await runFromLinked({ task: 'x', worktree: repo });
  assert.match(refused.content[0].text, /refused/i);
  assert.match(refused.content[0].text, /primary worktree/i);

  console.log('pi-antigravity: PASS');
} finally {
  rmSync(temp, { recursive: true, force: true });
}
