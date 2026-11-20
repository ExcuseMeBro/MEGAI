import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { existsSync } from 'node:fs';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const extension = fileURLToPath(new URL('../agent/extensions/megai-budget-guard/index.ts', import.meta.url));
const pi = process.env.MEGAI_BUDGET_GUARD_TEST_PI || 'pi';

function startPi(env, cwd) {
  const child = spawn(pi, ['--offline', '--mode', 'rpc', '--no-session', '--no-tools', '--no-context-files', '--no-skills',
    '--no-prompt-templates', '--no-themes', '--no-extensions', '-e', extension], { cwd, env, stdio: 'pipe' });
  const closed = once(child, 'close').catch(() => []);
  const reader = createInterface({ input: child.stdout });
  const events = [];
  let stderr = '', fault, wake;
  reader.on('line', line => { try { events.push(JSON.parse(line)); } catch { fault = new Error('Non-JSON RPC output'); } wake?.(); });
  child.on('error', err => { fault = err; wake?.(); });
  child.stderr.on('data', chunk => { if (stderr.length < 2500) stderr += chunk; });
  child.on('close', (code, sig) => { fault ??= new Error(`Pi exited ${code ?? sig}: ${stderr}`); wake?.(); });
  async function find(pred) {
    while (!fault) {
      const hit = events.find(pred);
      if (hit) return hit;
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`No matching RPC event. ${stderr}`)), 8000);
        wake = () => { clearTimeout(timer); wake = undefined; resolve(); };
      });
    }
    throw fault;
  }
  let id = 0;
  return {
    async command(text) {
      const key = String(++id), from = events.length;
      child.stdin.write(JSON.stringify({ id: key, type: 'prompt', message: text }) + '\n');
      const response = await find(e => e.type === 'response' && e.id === key);
      assert.equal(response.success, true, response.error);
      assert.equal(response.data.disposition, 'handled');
      const notify = await find((e, i) => i >= from && e.type === 'extension_ui_request' && e.method === 'notify');
      assert.equal(events.some(e => e.type === 'agent_start'), false, 'no model turn');
      return notify.message;
    },
    async close() { child.stdin.end(); child.kill(); await closed; reader.close(); },
  };
}

test('Pi 1.5.2 loads the budget guard and answers /budget without a model turn', { timeout: 30_000 }, async t => {
  const root = await mkdtemp(join(tmpdir(), 'budget-guard-native-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const home = join(root, 'home'), config = join(home, 'agent'), cwd = join(root, 'repo');
  await mkdir(config, { recursive: true }); await mkdir(cwd, { recursive: true });
  await writeFile(join(config, 'settings.json'), '{}\n');
  const base = { PATH: process.env.PATH, HOME: home, XDG_CONFIG_HOME: join(home, 'config'), XDG_CACHE_HOME: join(home, 'cache'),
    XDG_DATA_HOME: join(home, 'data'), PI_CODING_AGENT_DIR: config, PI_OFFLINE: '1', TERM: 'dumb' };

  const observe = startPi(base, cwd);
  t.after(() => observe.close());
  assert.match(await observe.command('/budget'), /^Budget guard \(observe\) — this session: \$0\.00, 0 requests/);
  assert.match(await observe.command('/budget week'), /Observe mode changed nothing/);
  assert.match(await observe.command('/budget nope'), /^Budget guard: \/budget/);
  await observe.close();

  const off = startPi({ ...base, MEGAI_BUDGET_GUARD: 'off' }, cwd);
  t.after(() => off.close());
  assert.match(await off.command('/budget'), /Budget guard is off/);
  await off.close();
  assert.equal(existsSync(join(config, 'budget-guard', 'outputs')), false, 'no capped outputs without tool calls');
});
