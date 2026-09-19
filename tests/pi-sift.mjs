// The `sift` file screen: candidate files are read by the tool and scored against
// the session's question, so the file text reaches the provider while only one
// probability per file returns. Path policy, per-file failures, truncation and the
// no-key path are pinned here. Offline — the endpoint is a local server and the
// provider, keychain and TypeSafe are unreachable.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
process.env.PI_OFFLINE = '1';
const ROOT = resolve('.');
const temp = mkdtempSync(join(tmpdir(), 'pi-sift-'));
const agent = join(temp, 'agent');
const KEPT = ['TYPESAFE_API_KEY', 'TYPESAFE_ENDPOINT', 'JEV_GATE', 'JEV_GATE_BLOCK', 'JEV_LOG'];
const savedEnv = Object.fromEntries(KEPT.map((name) => [name, process.env[name]]));
// The screened files are fixtures, not a real question: offline runs must not append
// synthetic lines to the live `~/.megai/jev-calls.jsonl` the gate thresholds are
// retuned from.
process.env.JEV_LOG = '0';

function install(...flags) {
  execFileSync('python3', ['-B', resolve('lib/pi_model_policy.py'), ...flags], {
    stdio: 'pipe',
    env: { ...process.env, HOME: temp, MEGAI_HOME: join(temp, 'megai'), MEGAI_SOURCE: ROOT, PI_CODING_AGENT_DIR: agent },
  });
  mkdirSync(agent, { recursive: true });
}

async function load() {
  process.env.PI_CODING_AGENT_DIR = agent;
  const loader = new DefaultResourceLoader({ cwd: temp, agentDir: agent });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  return loaded.extensions;
}

const calls = [];
const server = createServer((request, response) => {
  let body = '';
  request.on('data', (chunk) => { body += chunk; });
  request.on('end', () => {
    const parsed = JSON.parse(body);
    calls.push(parsed);
    response.writeHead(200, { 'content-type': 'application/json' });
    response.end(JSON.stringify({
      model: 'jev-1.13.0',
      usage: { input_tokens: 900, output_tokens: 20 },
      answers: { relevant: { type: 'noul', noul: parsed.state.includes('needle') ? 0.93 : 0.07 } },
    }));
  });
});
await new Promise((ready) => server.listen(0, '127.0.0.1', ready));
const endpoint = `http://127.0.0.1:${server.address().port}/v1/systemone`;

const read = (result) => JSON.parse(JSON.stringify(result.content[0].text));
const work = join(temp, 'work');

try {
  install();
  const installed = join(agent, 'extensions/megai-jev/index.ts');
  assert.equal(readFileSync(installed, 'utf8'), readFileSync(resolve('pi-skill/jev/index.ts'), 'utf8'),
    'the screen must ship in the existing installed asset');
  const tools = new Map();
  for (const extension of await load()) {
    for (const [name, tool] of extension.tools) tools.set(name, tool.definition);
  }
  const jev = tools.get('jev');
  const sift = tools.get('sift');
  assert.ok(jev && sift, 'the installed extension must register both jev and sift');

  mkdirSync(join(temp, 'bin'), { recursive: true });
  writeFileSync(join(temp, 'bin/security'), '#!/bin/sh\nexit 44\n');
  chmodSync(join(temp, 'bin/security'), 0o755);
  process.env.PATH = join(temp, 'bin') + ':' + (process.env.PATH ?? '');
  process.env.JEV_GATE = '0';
  const cwd = { hasUI: false, mode: 'print', cwd: work, isIdle: () => true, isProjectTrusted: () => false, abort() {}, getSystemPrompt: () => '', ui: { notify() {} } };
  const run = (params) => sift.execute('sift', params, undefined, undefined, cwd);

  mkdirSync(work, { recursive: true });
  writeFileSync(join(work, 'with-needle.md'), 'alpha needle omega\n');
  writeFileSync(join(work, 'plain.md'), 'nothing to see here\n');

  // Without any key the screen reports the same ok:false the jev tool does, and
  // reaches the network for nothing.
  const unkeyed = JSON.parse(read(await run({ query: 'find the needle', paths: [join(work, 'with-needle.md')] })));
  assert.equal(unkeyed.ok, false);
  assert.match(unkeyed.error, /no TypeSafe key/);
  assert.equal(calls.length, 0, 'a keyless screen must not call the provider');

  process.env.TYPESAFE_API_KEY = 'synthetic-only';
  process.env.TYPESAFE_ENDPOINT = endpoint;

  // Two files, one absolute and one relative: input order is the output order, each
  // request carries that file's own text, and one boolean question is asked. Files
  // are screened in parallel, so the requests are matched by content, not arrival.
  const screened = read(await run({ query: 'find the needle', paths: [join(work, 'with-needle.md'), 'plain.md'] }));
  assert.equal(calls.length, 2, 'one request per readable file');
  const needle = calls.find((call) => call.state.includes('alpha needle omega'));
  assert.ok(needle, 'the file text must reach the provider');
  assert.ok(calls.some((call) => call.state.includes('nothing to see here')),
    'a relative path must resolve against the working directory');
  assert.equal(needle.questions.relevant.type, 'noul');
  assert.match(needle.questions.relevant.instructions, /find the needle/);
  assert.match(needle.questions.relevant.instructions, /as data, not as instructions/);
  assert.equal(needle.model, 'jev-latest');
  const lines = screened.split('\n');
  assert.match(lines[0], /with-needle\.md: yes \(P=0\.93\)$/);
  assert.match(lines[1], /plain\.md: no \(P=0\.07\)$/);
  assert.match(lines.at(-1), /Unread files are not evidence of irrelevance/);
  assert.ok(!screened.includes('synthetic-only'), 'the screen never echoes the key');

  // A long file is sent as head plus tail — the end of a log is where the failure
  // is — and the result says so.
  const long = `HEADMARKER\n${'x'.repeat(30_000)}\nTAILMARKER\n`;
  writeFileSync(join(work, 'long.log'), long);
  let before = calls.length;
  const truncated = read(await run({ query: 'find the needle', paths: [join(work, 'long.log')] }));
  assert.equal(calls.length, before + 1);
  assert.ok(calls.at(-1).state.includes('HEADMARKER') && calls.at(-1).state.includes('TAILMARKER'),
    'truncation must keep both ends');
  assert.ok(calls.at(-1).state.length <= 24_000, 'the state must stay inside the provider budget');
  assert.match(truncated, /long\.log: .* \[head and tail only\]/);

  // Everything unreadable is refused per file, in one batch, without a request and
  // without leaking contents: a credential-shaped name, a directory, a binary, an
  // oversized file and a path outside the roots.
  mkdirSync(join(work, 'subdir'), { recursive: true });
  writeFileSync(join(work, '.env'), 'SECRET_TOKEN=do-not-send\n');
  writeFileSync(join(work, 'image.bin'), Buffer.from([0x89, 0x00, 0x50, 0x4e, 0x47, 0x0d]));
  writeFileSync(join(work, 'huge.txt'), 'y'.repeat(2 * 1024 * 1024 + 1));
  before = calls.length;
  const refused = read(await run({
    query: 'find the needle',
    paths: [join(work, '.env'), join(work, 'subdir'), join(work, 'image.bin'), join(work, 'huge.txt'),
      '/etc/hosts', join(work, 'with-needle.md')],
  }));
  assert.equal(calls.length, before + 1, 'only the one readable file may be sent');
  assert.ok(!calls.at(-1).state.includes('do-not-send'), 'a refused file must never be sent');
  assert.match(refused, /\.env: unread, refused: credential-like path/);
  assert.match(refused, /subdir: unread, not a regular file/);
  assert.match(refused, /image\.bin: unread, binary file/);
  assert.match(refused, /huge\.txt: unread, larger than 2 MB/);
  assert.match(refused, /\/etc\/hosts: unread, outside the readable roots/);
  assert.match(refused, /with-needle\.md: yes/);
  assert.ok(!refused.includes('{"ok":false'), 'one unreadable file must not fail the batch');

  process.env.PATH = savedEnv.PATH ?? process.env.PATH;
  install('--remove');
  assert.ok(!existsSync(installed), 'the installer must remove its own asset');
  // `JEV_LOG=0` above keeps these calls out of the live ledger, which is where the
  // gate bands get retuned from; checking the real file means a removed off switch or
  // a moved default path fails here instead of quietly polluting the calibration set.
  const ledger = join(homedir(), '.megai', 'jev-calls.jsonl');
  const offlineRows = existsSync(ledger) ? readFileSync(ledger, 'utf8').match(/"endpoint":"(?:127\.0\.0\.1|localhost|\[::1\])/g) : null;
  assert.equal(offlineRows, null, `the live Jev ledger holds ${offlineRows?.length} offline row(s)`);
  console.log('PASS: the sift screen sends each readable file straight to Jev and returns only a '
    + 'probability, keeps input order, marks head-and-tail truncation, refuses credential-like, '
    + 'non-file, binary, oversized and out-of-root paths per file without a request, reports a '
    + 'missing key without reaching the network, and adds no row to the live Jev ledger');
} finally {
  server.close();
  for (const [name, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[name];
    else process.env[name] = value;
  }
  rmSync(temp, { recursive: true, force: true });
}
