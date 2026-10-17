import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { performance } from 'node:perf_hooks';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
import { startFixture, acceptance } from './fixture.mjs';
import { startBridge } from './browser-bridge.mjs';
import { piUsage, e2eUsage } from './metrics.mjs';

const cwd = path.dirname(fileURLToPath(import.meta.url));
const mode = process.argv[2] ?? 'preflight';
const root = path.resolve(process.argv[3] ?? path.join(os.homedir(), '.megai/benchmarks/pi-e2e-' + Date.now()));
await fs.mkdir(root, { recursive: true, mode: 0o700 });
const snapshot = path.join(root, 'measured-source');
const frozenFiles = ['bench.mjs', 'metrics.mjs', 'summarize.mjs', 'fixture.mjs', 'browser-bridge.mjs', 'browser.mjs', 'saved-playwright.mjs', 'e2e.config.ts', 'package.json', 'package-lock.json', 'tests/flow.e2e.ts'];
let snapshotExists = true;
try { await fs.access(snapshot); } catch { snapshotExists = false; }
const checksums = [];
for (const file of frozenFiles) {
  const source = await fs.readFile(path.join(cwd, file));
  const destination = path.join(snapshot, file);
  if (snapshotExists) {
    const frozen = await fs.readFile(destination);
    if (!source.equals(frozen)) throw new Error('Source changed after preflight: ' + file);
  } else {
    await fs.mkdir(path.dirname(destination), { recursive: true, mode: 0o700 });
    await fs.writeFile(destination, source, { mode: 0o600 });
  }
  checksums.push(crypto.createHash('sha256').update(source).digest('hex') + '  ' + file);
}
if (!snapshotExists) await fs.writeFile(path.join(snapshot, 'SHA256SUMS'), checksums.join('\n') + '\n', { mode: 0o600 });
const auth = JSON.parse(await fs.readFile(path.join(process.env.PI_CODING_AGENT_DIR ?? path.join(os.homedir(), '.pi/agent'), 'auth.json'), 'utf8'))['openai-codex'];
if (auth?.type !== 'oauth' || auth.expires < Date.now() + 3600000) throw new Error('A current native ChatGPT login with at least one hour left is required; no login or refresh performed');
const { type: _type, ...credentials } = auth;
const env = { ...process.env, E2E_TELEMETRY_DISABLED: '1', E2E_OAUTH_CREDENTIALS: JSON.stringify({ openai: credentials }) };

async function execute(command, args, directory, trialEnv, prefix, timeout = 300000) {
  const begin = performance.now();
  const child = spawn(command, args, { cwd: directory, env: trialEnv, stdio: ['ignore', 'pipe', 'pipe'], detached: true });
  const stdout = [];
  const stderr = [];
  let timedOut = false;
  child.stdout.on('data', (data) => stdout.push(data));
  child.stderr.on('data', (data) => stderr.push(data));
  const timer = setTimeout(() => {
    timedOut = true;
    process.kill(-child.pid, 'SIGTERM');
  }, timeout);
  const force = setTimeout(() => { if (timedOut) process.kill(-child.pid, 'SIGKILL'); }, timeout + 5000);
  let code;
  try {
    code = await new Promise((resolve, reject) => { child.on('exit', resolve); child.on('error', reject); });
  } finally { clearTimeout(timer); clearTimeout(force); }
  const wallSeconds = (performance.now() - begin) / 1000;
  const out = Buffer.concat(stdout).toString('utf8');
  const err = Buffer.concat(stderr).toString('utf8');
  await fs.writeFile(prefix + '.stdout', out, { mode: 0o600 });
  await fs.writeFile(prefix + '.stderr', err, { mode: 0o600 });
  return { code, timedOut, wallSeconds, out, err };
}

const piArgs = ['-p', '--mode', 'json', '--no-session', '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-themes', '--no-context-files', '--tools', 'bash', '--model', 'openai-codex/gpt-6.1-sol', '--thinking', 'high', '--offline', '-a'];
const parseEvents = (text) => text.split('\n').filter(Boolean).map((line) => JSON.parse(line));
const task = 'Sign in with email bench@example.test and password demo-password. Then create a new project named Bench Project with description Token and speed benchmark. Verify visible success status Project created and heading Bench Project.';
const directPrompt = `Browser benchmark. ${task}
Use only the Playwright browser bridge through bash, never read source files or call the app HTTP endpoints directly. No delegation or configuration changes. Execute browser actions, do not write a test script.
Command: node browser.mjs '<JSON array of commands>'
Commands: {"op":"open"} opens the login page; {"op":"snapshot"} observes current page; {"op":"fill","label":"visible label","value":"text"}; {"op":"click","role":"button or link","name":"visible name"}; {"op":"assert","role":"heading","name":"expected heading"}.
Each invocation returns URL, accessible page snapshot, and page errors. Batch independent actions when possible. Inspect the actual page before deciding actions. Finish with a one-line outcome. Working directory is already configured.`;
const e2ePrompt = `Browser benchmark. ${task}
The existing frozen e2e test implements this exact flow, with agent.act and deterministic assertions. Run it once, do not edit or inspect source or configuration and do not delegate.
Command: ./node_modules/.bin/e2e run --output "$BENCH_E2E_OUTPUT"
Read the outcome and finish with a one-line pass/fail summary. No extra commands.`;
const savedPrompt = `Browser benchmark. ${task}
The existing frozen Playwright test implements this exact flow with deterministic assertions. Run it once, do not edit or inspect source or configuration and do not delegate.
Command: node saved-playwright.mjs
Read the outcome and finish with a one-line pass/fail summary. No extra commands.`;

async function trial(arm, rep, standalone = false) {
  const id = arm + '-' + rep;
  const directory = path.join(root, id);
  await fs.mkdir(directory, { mode: 0o700 });
  const fixture = await startFixture();
  const bridge = arm === 'pi-live' ? await startBridge(fixture.url) : undefined;
  const localEvidence = path.join(cwd, '.evidence', crypto.createHash('sha256').update(root).digest('hex').slice(0, 16));
  await fs.mkdir(localEvidence, { recursive: true, mode: 0o700 });
  const trialEnv = { ...env, BENCH_APP_URL: fixture.url, BENCH_BRIDGE_URL: bridge?.url, BENCH_CACHE_DIR: path.join(localEvidence, 'cache-' + rep), BENCH_E2E_OUTPUT: path.join(localEvidence, id), BENCH_REQUEST_RECEIPT: path.join(directory, 'e2e-requests.jsonl') };
  const prompt = arm === 'pi-live' ? directPrompt : arm === 'pi-saved' ? savedPrompt : e2ePrompt;
  await fs.writeFile(path.join(directory, 'prompt.txt'), prompt, { mode: 0o600 });
  let record;
  try {
    const run = standalone
      ? await execute(path.join(cwd, 'node_modules/.bin/e2e'), ['run', '--output', trialEnv.BENCH_E2E_OUTPUT], cwd, trialEnv, path.join(directory, 'native'))
      : await execute('pi', [...piArgs, prompt], cwd, trialEnv, path.join(directory, 'pi'));
    const pi = standalone ? { total: 0, calls: 0, cacheRead: 0, models: [], errors: [] } : piUsage(parseEvents(run.out));
    let nested = { total: 0, calls: 0, cacheRead: 0, models: [], cache: [], statuses: [] };
    if (arm.startsWith('e2e')) {
      await fs.cp(trialEnv.BENCH_E2E_OUTPUT, path.join(directory, 'e2e'), { recursive: true });
      nested = e2eUsage(JSON.parse(await fs.readFile(path.join(trialEnv.BENCH_E2E_OUTPUT, 'report.json'), 'utf8')));
    }
    record = { id, arm, rep, wallSeconds: run.wallSeconds, code: run.code, timedOut: run.timedOut, passed: run.code === 0 && !run.timedOut && pi.errors.length === 0 && acceptance(fixture.state) && (!arm.startsWith('e2e') || (nested.statuses.length === 1 && nested.statuses[0] === 'passed')), pi, e2e: nested, totalTokens: pi.total + nested.total, cacheReadTokens: pi.cacheRead + nested.cacheRead, state: fixture.state, browserOperations: bridge?.operations, browserErrors: bridge?.errors };
    await fs.writeFile(path.join(directory, 'record.json'), JSON.stringify(record, null, 2), { mode: 0o600 });
    await fs.appendFile(path.join(root, 'records.jsonl'), JSON.stringify(record) + '\n', { mode: 0o600 });
    console.log(JSON.stringify({ id, passed: record.passed, seconds: +record.wallSeconds.toFixed(2), tokens: record.totalTokens, piCalls: pi.calls, e2eCalls: nested.calls, cache: nested.cache }));
  } finally {
    if (bridge) await bridge.close();
    await new Promise((resolve) => fixture.server.close(resolve));
  }
  return record;
}

console.log('Evidence: ' + root);
if (mode === 'preflight') {
  const native = await execute('pi', [...piArgs, 'Respond only READY. No tool calls.'], cwd, env, path.join(root, 'pi-ready'), 120000);
  const usage = piUsage(parseEvents(native.out));
  if (native.code !== 0 || usage.calls !== 1 || usage.errors.length) throw new Error('Pi native preflight failed');
  console.log('Pi identity verified: ' + usage.models.join(', '));
  const list = await execute(path.join(cwd, 'node_modules/.bin/e2e'), ['models', 'openai'], cwd, env, path.join(root, 'e2e-models'), 30000);
  if (list.code !== 0 || !list.out.includes('gpt-6.1-sol')) throw new Error('e2e subscription does not serve the requested model');
  console.log('e2e native subscription model available: gpt-6.1-sol');
  const result = await trial('e2e-preflight', path.basename(root), true);
  if (!result.passed || result.e2e.calls === 0) throw new Error('e2e live preflight failed; inspect private evidence');
} else if (mode === 'run') {
  for (let rep = 1; rep <= 3; rep++) {
    const order = rep % 2 === 1 ? ['pi-live', 'e2e-cold', 'e2e-warm', 'pi-saved'] : ['e2e-cold', 'e2e-warm', 'pi-saved', 'pi-live'];
    for (const arm of order) {
      const result = await trial(arm, rep);
      if (!result.passed) throw new Error(result.id + ' failed; stop instead of silently retrying');
      if (arm === 'e2e-cold' && result.e2e.calls === 0) throw new Error('Cold run unexpectedly replayed');
      if (arm === 'e2e-warm' && (result.e2e.calls !== 0 || !result.e2e.cache.some((c) => c.mode === 'self-finalized'))) throw new Error('Warm run was not pure replay');
    }
  }
} else throw new Error('Use preflight or run');
