import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync, unlinkSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { DIFF_LIMIT, REVIEW_GATE, blockReason, cellCommands, checkPush, checkReviewed, checkSize, countChanged, diffLimit, findDevPushes, findWeakening, patchIdOf, reviewGate, reviewReason, sizeReason, toolCommands } from '../pi-defaults/extensions/megai-test-guard/guard.mjs';
import { patchId } from '../pi-defaults/opt-in/factory/review.ts';
import { piPackageRoot } from './pi-package.mjs';

const extensionPath = fileURLToPath(new URL('../pi-defaults/extensions/megai-test-guard/index.ts', import.meta.url));
const diff = (path, { added = [], removed = [], deleted = false } = {}) => [
  `diff --git a/${path} b/${path}`, ...(deleted ? ['deleted file mode 100644'] : []), `--- a/${path}`, `+++ b/${path}`, '@@ -1 +1 @@',
  ...removed.map((l) => `-${l}`), ...added.map((l) => `+${l}`),
].join('\n');

test('findings: skip/focus markers, deleted tests, dropped assertions, non-blocking CI', () => {
  const cases = [
    [diff('src/a.test.ts', { added: ["it.skip('parses', () => {"] }), /skip\/only marker/],
    [diff('src/a.spec.js', { added: ["describe.only('x', () => {"] }), /skip\/only marker/],
    [diff('web/__tests__/b.tsx', { added: ["xit('renders', () => {"] }), /skip\/focus marker/],
    [diff('tests/test_api.py', { added: ['@pytest.mark.xfail(reason="flaky")'] }), /pytest/],
    [diff('app/models_test.py', { added: ['    self.skipTest("later")'] }), /pytest\/unittest/],
    [diff('pkg/x_test.go', { added: ['\tt.Skip("broken")'] }), /Go t.Skip/],
    [diff('src/lib.rs', { added: ['#[ignore]'] }), /Rust/],
    [diff('app/src/test/java/FooTest.java', { added: ['  @Disabled'] }), /JUnit/],
    [diff('tests/test_old.py', { deleted: true, removed: ['def test_a(): assert f()'] }), /test file deleted/],
    [diff('tests/test_calc.py', { removed: Array(5).fill('assert add(1, 2) == 3') }), /5 assertions removed/],
    [diff('.github/workflows/ci.yml', { added: ['        continue-on-error: true'] }), /continue-on-error/],
    [diff('.github/workflows/ci.yml', { added: ['      - run: npm test || true'] }), /non-blocking/],
    [diff('package.json', { added: ['    "test": "jest --passWithNoTests"'] }), /passWithNoTests/],
  ];
  for (const [text, expected] of cases) {
    const found = findWeakening(text);
    assert.equal(found.length, 1, `${text}\n→ ${found}`);
    assert.match(found[0], expected);
  }
});

test('findings: ordinary code and test changes pass', () => {
  const clean = [
    diff('src/a.ts', { added: ['const skip = (n) => n + 1;', "if (opts.only) run('x');"] }),
    diff('src/a.test.ts', { added: ["it('parses dates', () => {", '  expect(parse(x)).toEqual(y);'], removed: ['  expect(parse(x)).toBe(y);'] }),
    diff('tests/test_calc.py', { removed: ['assert add(1, 2) == 3', 'assert add(0, 0) == 0'], added: ['assert add(1, 2) == 3'] }),
    diff('src/old_module.py', { deleted: true, removed: ['def f(): pass'] }),
    diff('docs/testing.md', { added: ['Use `it.skip(` sparingly.'] }),
    diff('.github/workflows/ci.yml', { added: ['      - run: npm test'] }),
    diff('web/app.js', { added: ['fit($("#p-comment"));'] }),
    ['diff --git a/x_test.go b/x_test.go', 'new file mode 100644', '+++ b/x_test.go', '+\tt.Skip("broken")'].join('\n'),
    diff('api/db_test.go', { added: ['\t\tt.Skip("ALFA_OTP_TEST_DSN not set")'] }),
    diff('tests/test_shell.py', { added: ['@unittest.skipUnless(shutil.which("pwsh"), "PowerShell is not installed")'] }),
    diff('e2e/write.spec.ts', { added: ['test.skip(!writeEnabled, writeSkipReason);'] }),
    diff('tests/test_old.py', { deleted: true }) + '\n' + diff('src/old.py', { deleted: true }),
    diff('docs/specs/plan.md', { deleted: true }),
    diff('tests/test_flow.py', { removed: Array(6).fill('assert x'), added: Array(2).fill('assert y') }),
  ];
  for (const text of clean) assert.deepEqual(findWeakening(text), [], text);
});

test('command parsing: dev pushes in common shapes, data and other targets ignored', () => {
  const cwd = '/work/repo';
  const pushes = (command) => findDevPushes(command, cwd).map(({ dir, remote, src, dst }) => `${dir}|${remote}|${src}|${dst}`);
  assert.deepEqual(pushes('git push origin dev'), ['/work/repo|origin|dev|dev']);
  assert.deepEqual(pushes('cd /other && git fetch -q && git merge --ff-only task/x && git push -q origin dev'), ['/other|origin|dev|dev']);
  assert.deepEqual(pushes('git -C ../sibling push origin HEAD:refs/heads/dev'), ['/work/sibling|origin|HEAD|dev']);
  assert.deepEqual(pushes('GIT_TRACE=0 git -c core.x=1 push upstream abc123:dev 2>&1 | tail -3'), ['/work/repo|upstream|abc123|dev']);
  assert.deepEqual(pushes('(cd sub && git push)'), ['/work/repo/sub|origin|HEAD|@current']);
  assert.deepEqual(pushes('git push origin task/x'), []);
  assert.deepEqual(pushes('git push --all origin'), ['/work/repo|origin|dev|dev']);
  assert.deepEqual(pushes('git push --mirror backup'), ['/work/repo|backup|dev|dev']);
  assert.deepEqual(pushes('git push origin --delete dev'), []);
  assert.deepEqual(pushes('echo "git push origin dev"'), []);
  assert.deepEqual(pushes('rg "git push origin dev" docs'), []);
  assert.deepEqual(pushes('cd "$repo" && git push origin dev'), ['null|origin|dev|dev']);
});

test('ipython cells: shell commands visible in the source are checked like bash', () => {
  const cwd = '/work/repo';
  const devPushes = (code) => cellCommands(code).flatMap((c) => findDevPushes(c, cwd)).map(({ dir, dst }) => `${dir}|${dst}`);
  assert.deepEqual(devPushes("r = await bash('git push origin dev', timeout=600)\nprint(r.output)"), ['/work/repo|dev']);
  assert.deepEqual(devPushes('import subprocess\nsubprocess.run(["git", "push", "origin", "dev"], check=True)'), ['/work/repo|dev']);
  assert.deepEqual(devPushes('import os\nos.system("cd /other && git push origin HEAD:refs/heads/dev")'), ['/other|dev']);
  assert.deepEqual(devPushes('bash("""git push -q origin dev""")'), ['/work/repo|dev']);
  assert.deepEqual(devPushes("bash('echo \\'ok\\' && git push origin dev')"), ['/work/repo|dev']);
  assert.deepEqual(devPushes('# git push origin dev\nprint(1)'), []);
  assert.deepEqual(devPushes("bash('git push origin task/x')"), []);
  assert.deepEqual(devPushes("print('push the button')"), []);
  // Computed strings are not visible (same limit as the ipython action-boundary bridge).
  assert.deepEqual(devPushes("b = 'dev'\nbash(f'git push origin {b}')"), []);
  assert.deepEqual(toolCommands({ toolName: 'bash', input: { command: 'git push origin dev' } }), ['git push origin dev']);
  assert.deepEqual(toolCommands({ toolName: 'ipython', input: { code: "bash('ls')" } }), ['ls']);
  assert.deepEqual(toolCommands({ toolName: 'read', input: { path: 'git push origin dev' } }), []);
});

function repo(t) {
  const base = realpathSync(mkdtempSync(join(tmpdir(), 'pi-test-guard-')));
  t.after(() => rmSync(base, { recursive: true, force: true }));
  const work = join(base, 'work');
  const run = (...args) => execFileSync('git', args, { cwd: work, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  execFileSync('git', ['init', '-q', '--bare', join(base, 'remote.git')]);
  mkdirSync(work);
  run('init', '-q', '-b', 'dev');
  run('config', 'user.email', 'guard@example.invalid');
  run('config', 'user.name', 'Guard');
  mkdirSync(join(work, 'tests'));
  writeFileSync(join(work, 'tests/test_calc.py'), 'def test_add():\n    assert 1 + 1 == 2\n');
  writeFileSync(join(work, 'calc.py'), 'def add(a, b):\n    return a + b\n');
  run('add', '-A'); run('commit', '-qm', 'base');
  run('remote', 'add', 'origin', join(base, 'remote.git'));
  run('push', '-q', 'origin', 'dev');
  return { base, work, run };
}

test('git range: weakening blocks, a Test-Change trailer or a clean range allows', (t) => {
  const { work, run } = repo(t);
  const push = { dir: work, remote: 'origin', src: 'dev', dst: 'dev' };
  assert.deepEqual(checkPush(push), [], 'nothing to push');
  writeFileSync(join(work, 'calc.py'), 'def add(a, b):\n    return a + b + 0\n');
  run('commit', '-qam', 'tweak');
  assert.deepEqual(checkPush(push), []);
  writeFileSync(join(work, 'tests/test_calc.py'), 'import pytest\n\n@pytest.mark.skip(reason="later")\ndef test_add():\n    assert 1 + 1 == 2\n');
  run('commit', '-qam', 'skip it');
  const findings = checkPush(push);
  assert.equal(findings.length, 1);
  assert.match(blockReason(findings), /Test-Change: <why>/);
  run('commit', '--amend', '-qm', 'skip it\n\nTest-Change: upstream API removed, test moved to integration suite');
  assert.deepEqual(checkPush(push), []);
  unlinkSync(join(work, 'tests/test_calc.py'));
  run('commit', '-qam', 'drop test');
  assert.deepEqual(checkPush(push), [], 'trailer anywhere in the pushed range covers it');
  assert.deepEqual(checkPush({ ...push, src: 'no-such-ref' }), [], 'unknown ref fails open');
  assert.deepEqual(checkPush({ ...push, dir: null }), [], 'unresolvable dir fails open');
});

test('review gate: only an approved change reaches dev, by patch-id; a clean rebase keeps the approval', async (t) => {
  const { base, work, run } = repo(t);
  t.after(() => { delete globalThis[REVIEW_GATE]; });
  const push = { dir: work, remote: 'origin', src: 'HEAD', dst: 'dev' };
  assert.equal(reviewGate({}), undefined, 'no gate outside a reviewed Factory run');
  assert.deepEqual(checkReviewed(push, undefined), []);
  run('switch', '-qc', 'task/x');
  writeFileSync(join(work, 'calc.py'), 'def add(a, b):\n    return b + a\n');
  run('commit', '-qam', 'candidate');
  const approved = await patchId(work, 'origin/dev', 'HEAD');
  assert.equal(approved, patchIdOf(work, 'refs/remotes/origin/dev', 'HEAD'), 'Factory and the guard compute the same id');
  globalThis[REVIEW_GATE] = { label: 'Factory p', approved: [] };
  const findings = checkReviewed({ ...push, src: 'task/x' }, reviewGate({}));
  assert.equal(findings.length, 1);
  assert.match(reviewReason(findings), /FACTORY_READY/);
  globalThis[REVIEW_GATE].approved.push(approved);
  assert.deepEqual(checkReviewed({ ...push, src: 'task/x' }, reviewGate({})), []);
  // Someone else lands on dev; the rebased candidate (new SHA) still has the approved change.
  const other = join(base, 'other');
  execFileSync('git', ['clone', '-q', '-b', 'dev', join(base, 'remote.git'), other]);
  writeFileSync(join(other, 'notes.txt'), 'unrelated\n');
  execFileSync('git', ['-C', other, 'add', 'notes.txt']);
  execFileSync('git', ['-C', other, '-c', 'user.email=o@example.invalid', '-c', 'user.name=O', 'commit', '-qm', 'notes']);
  execFileSync('git', ['-C', other, 'push', '-q', 'origin', 'dev']);
  run('fetch', '-q', 'origin');
  run('rebase', '-q', 'origin/dev');
  assert.deepEqual(checkReviewed({ ...push, src: 'task/x' }, reviewGate({})), []);
  // Any further change needs another review.
  writeFileSync(join(work, 'calc.py'), 'def add(a, b):\n    return b + a + 0\n');
  run('commit', '-qam', 'after review');
  assert.equal(checkReviewed({ ...push, src: 'task/x' }, reviewGate({})).length, 1);
  // Unlike the other checks the gate fails closed.
  assert.equal(checkReviewed({ ...push, dir: null }, reviewGate({})).length, 1);
  assert.equal(checkReviewed({ ...push, src: 'no-such-ref' }, reviewGate({})).length, 1);
  assert.deepEqual(checkReviewed({ ...push, src: 'origin/dev' }, reviewGate({})), [], 'nothing to push');
  // A preparation worker never pushes dev, even with an approval in its own process.
  assert.match(reviewGate({ MEGAI_FACTORY_PREP_WORKER: '1' }).label, /preparation worker/);
  assert.equal(checkReviewed({ ...push, src: 'task/x' }, reviewGate({ MEGAI_FACTORY_PREP_WORKER: '1' })).length, 1);
});

test('diff budget: counts changed lines without lockfiles and blocks only over the active limit', (t) => {
  assert.equal(countChanged('10\t2\tsrc/a.ts\n100\t50\tpackage-lock.json\n-\t-\timg.png\n3\t1\tsrc/{old => new}.ts\n5\t5\tx/{a => Cargo.lock}\n'), 16);
  const prior = process.env.MEGAI_DIFF_LIMIT;
  t.after(() => { delete globalThis[DIFF_LIMIT]; if (prior === undefined) delete process.env.MEGAI_DIFF_LIMIT; else process.env.MEGAI_DIFF_LIMIT = prior; });
  delete process.env.MEGAI_DIFF_LIMIT;
  assert.equal(diffLimit(), undefined);
  process.env.MEGAI_DIFF_LIMIT = '40';
  assert.deepEqual(diffLimit(), { lines: 40, label: 'MEGAI_DIFF_LIMIT' });
  globalThis[DIFF_LIMIT] = { lines: 5, label: 'routine p/deps' };
  assert.deepEqual(diffLimit(), { lines: 5, label: 'routine p/deps' }, 'Factory routine limit wins');
  const { work, run } = repo(t);
  const push = { dir: work, remote: 'origin', src: 'dev', dst: 'dev' };
  writeFileSync(join(work, 'calc.py'), 'def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n');
  writeFileSync(join(work, 'package-lock.json'), `${'{}\n'.repeat(500)}`);
  run('add', '-A'); run('commit', '-qm', 'sub');
  assert.deepEqual(checkSize(push, { lines: 5, label: 'routine p/deps' }), [], '4 added lines fit; the lockfile is excluded');
  const over = checkSize(push, { lines: 3, label: 'routine p/deps' });
  assert.deepEqual(over, ['4 changed lines exceed the 3-line budget of routine p/deps (lockfiles excluded)']);
  assert.match(sizeReason(over), /larger than this task allows/);
  assert.deepEqual(checkSize({ ...push, src: 'no-such-ref' }, { lines: 1, label: 'x' }), [], 'unknown ref fails open');
});

// The installed Pi SDK runs a real bash tool call from a faux model through the hook.
const root = piPackageRoot();
// A real Pi session with this extension (plus `extensions`) and a faux model.
async function piSession(t, work, { tools, extensions = [] }) {
  const { createAgentSession, DefaultResourceLoader, ModelRuntime, SessionManager, SettingsManager } =
    await import(pathToFileURL(join(root, 'dist/index.js')));
  const { fauxProvider, fauxAssistantMessage, fauxToolCall, InMemoryCredentialStore } =
    await import(pathToFileURL(join(dirname(root), 'pi-ai/dist/index.js')));
  const agentDir = join(dirname(work), 'agent');
  mkdirSync(agentDir);
  const prior = process.env.PI_CODING_AGENT_DIR;
  process.env.PI_CODING_AGENT_DIR = agentDir;
  const settingsManager = SettingsManager.inMemory({ compaction: { enabled: false } }, { projectTrusted: true });
  const resourceLoader = new DefaultResourceLoader({ cwd: work, agentDir, settingsManager,
    additionalExtensionPaths: [extensionPath, ...extensions], noSkills: true, noContextFiles: true, noPromptTemplates: true, noThemes: true });
  await resourceLoader.reload();
  assert.deepEqual(resourceLoader.getExtensions().errors, []);
  const modelRuntime = await ModelRuntime.create({ credentials: new InMemoryCredentialStore(),
    modelsPath: null, modelsStorePath: join(agentDir, 'models-cache.json'), refreshOnCreate: false });
  const faux = fauxProvider({ models: [{ id: 'fixture' }] });
  modelRuntime.registerNativeProvider(faux.provider);
  const { session } = await createAgentSession({ cwd: work, agentDir, resourceLoader, settingsManager, modelRuntime,
    model: faux.getModel(), thinkingLevel: 'low', sessionManager: SessionManager.inMemory(work), tools });
  t.after(() => {
    session.dispose();
    if (prior === undefined) delete process.env.PI_CODING_AGENT_DIR; else process.env.PI_CODING_AGENT_DIR = prior;
  });
  return { session, faux, fauxAssistantMessage, fauxToolCall };
}

test('native Pi: a bash push to dev that skips a test is blocked; the model sees why', { timeout: 60000 }, async (t) => {
  const { work, run } = repo(t);
  writeFileSync(join(work, 'tests/test_calc.py'), 'import pytest\n\n@pytest.mark.skip\ndef test_add():\n    assert 1 + 1 == 2\n');
  run('commit', '-qam', 'skip');
  const { session, faux, fauxAssistantMessage, fauxToolCall } = await piSession(t, work, { tools: ['bash'] });
  let toolResult = '';
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command: `cd ${JSON.stringify(work)} && git push -q origin dev` })),
    async (context) => {
      const last = context.messages.at(-1);
      toolResult = (last?.content ?? []).map((b) => b.text ?? '').join('\n');
      return fauxAssistantMessage('Understood.');
    },
  ]);
  await session.prompt('Deliver it');
  assert.match(toolResult, /megai-test-guard blocked this push/);
  assert.match(toolResult, /pytest/);
  const remoteHead = execFileSync('git', ['-C', join(dirname(work), 'remote.git'), 'rev-parse', 'dev'], { encoding: 'utf8' }).trim();
  assert.notEqual(remoteHead, run('rev-parse', 'HEAD'), 'the push did not happen');
});

// Pi-Bolt models also push from the ipython tool (`await bash('git push origin dev')`), which
// bypassed a bash-only hook. A stand-in ipython tool really runs the cell with python3.
test('native Pi: an ipython cell that pushes a skipped test to dev is blocked', { timeout: 60000 }, async (t) => {
  const { work, run } = repo(t);
  writeFileSync(join(work, 'tests/test_calc.py'), 'import pytest\n\n@pytest.mark.skip\ndef test_add():\n    assert 1 + 1 == 2\n');
  run('commit', '-qam', 'skip');
  const fakeIpython = join(dirname(work), 'fake-ipython.mjs');
  writeFileSync(fakeIpython, `import { spawnSync } from 'node:child_process';
const PRELUDE = 'import subprocess\\ndef bash(command, **_):\\n    return subprocess.run(command, shell=True, capture_output=True, text=True)\\n';
export default function (pi) {
  pi.registerTool({
    name: 'ipython', label: 'ipython', description: 'Run Python code.',
    parameters: { type: 'object', properties: { code: { type: 'string' } }, required: ['code'] },
    async execute(_id, params, _signal, _update, ctx) {
      const r = spawnSync('python3', ['-c', PRELUDE + params.code], { cwd: ctx?.cwd, encoding: 'utf8' });
      return { content: [{ type: 'text', text: 'exit ' + r.status + ' ' + r.stdout + r.stderr }], details: {} };
    },
  });
}
`);
  const { session, faux, fauxAssistantMessage, fauxToolCall } = await piSession(t, work, { tools: ['ipython'], extensions: [fakeIpython] });
  let toolResult = '';
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('ipython', { code: "r = bash('git push -q origin dev')\nprint(r.returncode)" })),
    async (context) => {
      toolResult = (context.messages.at(-1)?.content ?? []).map((b) => b.text ?? '').join('\n');
      return fauxAssistantMessage('Understood.');
    },
  ]);
  await session.prompt('Deliver it');
  assert.match(toolResult, /megai-test-guard blocked this push/);
  const remoteHead = execFileSync('git', ['-C', join(dirname(work), 'remote.git'), 'rev-parse', 'dev'], { encoding: 'utf8' }).trim();
  assert.notEqual(remoteHead, run('rev-parse', 'HEAD'), 'the push did not happen');
});

test('native Pi: with the Factory review gate active, an unapproved bash push to dev is blocked', { timeout: 60000 }, async (t) => {
  const { work, run } = repo(t);
  writeFileSync(join(work, 'calc.py'), 'def add(a, b):\n    return b + a\n');
  run('commit', '-qam', 'unreviewed');
  globalThis[REVIEW_GATE] = { label: 'Factory p', approved: [] };
  t.after(() => { delete globalThis[REVIEW_GATE]; });
  const { session, faux, fauxAssistantMessage, fauxToolCall } = await piSession(t, work, { tools: ['bash'] });
  let toolResult = '';
  faux.setResponses([
    fauxAssistantMessage(fauxToolCall('bash', { command: `cd ${JSON.stringify(work)} && git push -q origin dev` })),
    async (context) => {
      toolResult = (context.messages.at(-1)?.content ?? []).map((b) => b.text ?? '').join('\n');
      return fauxAssistantMessage('Understood.');
    },
  ]);
  await session.prompt('Deliver it');
  assert.match(toolResult, /independent review gate is active/);
  const remoteHead = execFileSync('git', ['-C', join(dirname(work), 'remote.git'), 'rev-parse', 'dev'], { encoding: 'utf8' }).trim();
  assert.notEqual(remoteHead, run('rev-parse', 'HEAD'), 'the push did not happen');
});
