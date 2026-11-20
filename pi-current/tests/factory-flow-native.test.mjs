import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { once } from 'node:events';
import { cp, mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const source = fileURLToPath(new URL('../agent/extensions/megai-factory-flow/', import.meta.url));
const pi = process.env.MEGAI_FACTORY_FLOW_TEST_PI || 'pi';
const a = '1'.repeat(40), b = '2'.repeat(40);
const stub = (id, more = {}) => ({ id, project:'demo', status:'todo', human:false, description:'', comments:0, updated_at:'2026-01-01T00:00:00Z', ...more });
const mark = (id, value) => ({ id, task_id:1, body:'Factory-Flow: '+JSON.stringify({v:1, ...value}) });
const wait = mark(1, {kind:'wait', key:'target', type:'decision', blocked:'Choose a test target', question:'Which test target?', recommendation:'Use the fixture', next:'Run an isolated check'});
const answer = mark(2, {kind:'answer', key:'target', answer:'Use the fixture'});
const receipt = mark(3, {kind:'receipt', stage:'remote-verified', sha:a, remote:'origin/example', remoteHead:b, checks:[{name:'test', status:'pass'}]});

function startPi({ env, cwd, extension }) {
  const child = spawn(pi, ['--offline','--mode','rpc','--no-session','--no-tools','--no-context-files', '--no-skills', '--no-prompt-templates', '--no-themes',
    ...(extension ? ['--no-extensions', '-e', extension] : [])], { cwd, env, stdio:'pipe' });
  const closed = once(child, 'close').catch(() => []);
  const reader = createInterface({ input: child.stdout });
  const events = [];
  let stderr = '', fault, wake;
  const signal = () => wake?.();
  reader.on('line', line => {
    try { events.push(JSON.parse(line)); }
    catch { fault = new Error('Non-JSON output from native Pi RPC'); }
    signal();
  });
  child.on('error', err => { fault = err; signal(); });
  child.stdin.on('error', err => { fault = err; signal(); });
  child.stderr.on('data', chunk => { if (stderr.length < 2500) stderr += chunk; });
  child.on('close', (code, sig) => { fault ??= new Error(`Native Pi exited ${code ?? sig}: ${stderr}`); signal(); });
  async function find(predicate) {
    while (!fault) {
      const value = events.find(predicate);
      if (value) return value;
      await new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error(`No matching native Pi response. ${stderr}`)), 8000);
        wake = () => { clearTimeout(timer); wake = undefined; resolve(); };
      });
    }
    throw fault;
  }
  let id = 0;
  return {
    async call(type, fields = {}) {
      const key = String(++id), from = events.length;
      child.stdin.write(JSON.stringify({ id:key, type, ...fields })+'\n');
      const response = await find(item => item.type === 'response' && item.id === key);
      assert.equal(response.success, true, response.error);
      if (type !== 'prompt') return response.data;
      assert.equal(response.data.disposition, 'handled');
      const notify = await find((item, i) => i >= from && item.type === 'extension_ui_request' && item.method === 'notify');
      assert.equal(events.some(item => item.type === 'agent_start'), false, 'no model turn');
      return notify;
    },
    async close() { child.stdin.end(); child.kill(); await closed; reader.close(); },
  };
}

test('Pi 1.5.2 discovers Factory Flow and consumes all read-only commands across fresh sessions', {timeout:30_000}, async t => {
  const root = await mkdtemp(join(tmpdir(), 'factory-flow-native-'));
  const home = join(root,'home'), config = join(home,'agent'), cwd = join(root,'repo');
  const target = join(config,'extensions','megai-factory-flow');
  const env = {PATH:process.env.PATH, HOME:home, XDG_CONFIG_HOME:join(home,'config'), XDG_CACHE_HOME:join(home,'cache'),
    XDG_DATA_HOME:join(home,'data'), PI_CODING_AGENT_DIR:config, PI_OFFLINE:'1', TERM:'dumb'};
  const invoke = { env, cwd };
  const children = [];
  const start = opts => { const proc = startPi({...invoke, ...opts}); children.push(proc); return proc; };
  const requests = [];
  let comments = [wait];
  let truncated = false;
  const server = createServer((req, res) => {
    requests.push([req.method, req.url]);
    const reply = (body, status = 200) => { res.writeHead(status, {'Content-Type':'application/json'}); res.end(JSON.stringify(body)); };
    const first = stub(1, {comments:comments.length, description:'Factory depends-on: demo#4\nFactory required-checks: test'});
    if (req.method !== 'GET') return reply({}, 405);
    if (req.url === '/api/board?project=demo') return reply({ projects:[{slug:'demo', archived:false}], done_hidden:1,
      tasks:[first, stub(2, {human:true}), stub(3, {description:'Factory depends-on: demo#99'}), stub(5, {description:'Factory depends-on: demo#5'})] });
    if (req.url === '/api/tasks/1') return reply({ task:first, comments:truncated ? [] : comments });
    if (req.url === '/api/tasks/4') return reply({task:stub(4, {status:'done'}), comments:[]});
    return reply({}, 404);
  });
  t.after(async () => {
    await Promise.all(children.map(proc => proc.close()));
    if (server.listening) { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
    await rm(root, {recursive:true, force:true});
  });
  await mkdir(target, {recursive:true});
  await mkdir(join(cwd,'.pi'), {recursive:true});
  execFileSync('git', ['init','--quiet'], {cwd, env, timeout:2000});
  await writeFile(join(cwd,'.pi','project.json'), JSON.stringify({brokanProject:'demo'}));
  await writeFile(join(config,'settings.json'), JSON.stringify({defaultProjectTrust:'always', packages:[]}));
  await cp(source, target, {recursive:true});
  assert.equal(execFileSync(pi, ['--version'], {env, cwd, timeout:5000, encoding:'utf8'}).trim(), '1.5.2');
  const actual = start();
  const menu = await actual.call('get_commands');
  assert.equal(menu.commands.filter(command => command.name === 'factory-flow').length, 1);
  assert.match((await actual.call('prompt', {message:'/factory-flow help'})).message, /read-only.*needs.*receipt.*eval/);
  await actual.close();

  server.listen(0,'127.0.0.1');
  await once(server,'listening');
  const adapter = join(root, 'fixture-entry.ts');
  await writeFile(adapter, `import { registerFactoryFlow } from ${JSON.stringify(join(target,'index.ts'))};\nimport { reader } from ${JSON.stringify(join(target,'reader.mjs'))};\nexport default pi => registerFactoryFlow(pi, reader(${server.address().port}));\n`);
  const first = start({extension:adapter});
  const ask = (proc, command) => proc.call('prompt', {message:`/factory-flow ${command}`});
  assert.match((await ask(first, 'needs')).message, /demo#1 — needs you \[target\]: Which test target\?/);
  const before = (await ask(first, 'ready')).message;
  assert.match(before, /demo#1 — waiting: needs decision: target/);
  assert.doesNotMatch(before, /demo#2/);
  assert.match(before, /demo#3 — waiting: unknown demo#99/);
  assert.match(before, /demo#5 — waiting: cycle at demo#5/);
  assert.match((await ask(first, 'resume demo#1')).message, /Next after answer: Run an isolated check/);
  await first.close();

  comments = [wait, answer, receipt]; // Synthetic board state change, not an API write.
  const fresh = start({extension:adapter});
  assert.match((await ask(fresh, 'needs')).message, /No open Factory handoffs/);
  assert.match((await ask(fresh, 'resume demo#1')).message, /answer on task, not authorization.*Use the fixture/);
  assert.match((await ask(fresh, 'ready')).message, /demo#1 — ready for manual review/);
  assert.match((await ask(fresh, `receipt demo#1 ${a}`)).message, /Remote attestation \(not re-fetched\): origin\/example/);
  assert.match((await ask(fresh, `receipt demo#1 ${b}`)).message, /no receipt for this exact SHA/);
  const sample = {base:a, fixture:'3'.repeat(64), setup:'4'.repeat(64), accepted:true, regressions:0, ms:210, usdMicros:null};
  await writeFile(join(cwd,'paired sample.json'), JSON.stringify({v:1, arms:['control','trial'], cases:[{
    id:'synthetic', runs:[{...sample,arm:'control'},{...sample,arm:'trial',ms:160,regressions:1}]
  }]}));
  const report = (await ask(fresh, 'eval paired sample.json')).message;
  assert.match(report, /comparable costs for 0/);
  assert.match(report, /control: accepted 1\/1.*210 ms median.*cost unavailable/);
  assert.match(report, /trial: accepted 0\/1.*160 ms median.*faster in 1\/1/);
  const count = requests.length;
  assert.equal((await ask(fresh, 'resume other#1')).notifyType, 'error');
  assert.deepEqual(requests.slice(count), [['GET','/api/board?project=demo']]);
  truncated = true;
  assert.match((await ask(fresh, 'ready')).message, /demo#1 — waiting: Factory records not verified/);
  assert.equal((await ask(fresh, 'resume demo#1')).notifyType, 'error');
  assert.ok(requests.length && requests.every(([method]) => method === 'GET'));
});
