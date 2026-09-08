// Exercise the actual Pi extension loader/hooks. No provider, model or real memory calls.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, copyFileSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const packageRoot = process.env.PI_PACKAGE_ROOT;
assert.ok(packageRoot, 'Set PI_PACKAGE_ROOT to the installed @earendil-works/pi-coding-agent directory');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')));
const temporary = mkdtempSync(join(tmpdir(), 'headroom-extension-'));
const originalRoot = process.env.MEGAI_HOME;
process.env.MEGAI_HOME = temporary;
process.env.PI_OFFLINE = '1';
process.env.OPENAI_API_KEY = 'synthetic-never-forward';
const binary = join(temporary, 'venv/headroom/bin/python');
mkdirSync(resolve(binary, '..'), { recursive: true });
writeFileSync(binary, `#!/usr/bin/env node
const fs=require('node:fs'); let text='';
process.stdin.on('data', x=>text+=x);
process.stdin.on('end', ()=> {
 const q=JSON.parse(text); const root=process.env.MEGAI_HOME;
 if(process.env.OPENAI_API_KEY) process.exit(9);
 fs.appendFileSync(root+'/calls', q.action+'\\n');
 const r=q.action==='steering' ? {text:'Headroom concise fixture'} :
 q.action==='compress' ? {text:'compact fixture',compressed:true,id:'123456789abcdef123456789'} :
 q.action==='retrieve' ? {text:'exact fixture',next_offset:null} : {memories:[]};
 process.stdout.write(JSON.stringify(r));
});
`, { mode: 0o700 });
try {
 const loader = new DefaultResourceLoader({ cwd: temporary, agentDir: join(temporary, 'agent'),
   settingsManager: SettingsManager.inMemory({ packages: [] }),
   additionalExtensionPaths: [resolve('pi-skill/headroom/index.ts')],
 });
 await loader.reload();
 const loaded = loader.getExtensions();
 assert.deepEqual(loaded.errors, []);
 assert.equal(loaded.extensions.length, 1);
 const extension = loaded.extensions[0];
 const invoke = async (name, event = {}) => {
   let result;
   for (const handler of extension.handlers.get(name) || []) result = await handler(event, ctx);
   return result;
 };
 const notices = [];
 const ctx = { cwd: temporary, hasUI: true, ui: { notify: text => notices.push(text) },
   model: { id: 'preserve-model', provider: 'openai-codex' }, thinkingLevel: 'high' };
 await invoke('session_start');
 assert.equal(extension.handlers.has('before_provider_request'), false);
 assert.equal(extension.handlers.has('before_provider_headers'), false);
 assert.equal(extension.handlers.has('tool_result'), false);
 let shaped = await invoke('before_agent_start', { systemPrompt: 'unchanged policy' });
 assert.ok(shaped.systemPrompt.startsWith('unchanged policy'));
 assert.ok(shaped.systemPrompt.includes('Headroom concise fixture'));
 await invoke('input', { text: 'normal mode' });
 assert.equal(await invoke('before_agent_start', { systemPrompt: 'unchanged policy' }), undefined);
 const raw = 'synthetic original '.repeat(300);
 const pair = (id, name, args, isError = false) => [
   {role:'assistant',content:[{type:'toolCall',id,name,arguments:args}]},
   {role:'toolResult',toolCallId:id,toolName:name,isError,content:[{type:'text',text:raw}],timestamp:1},
 ];
 const event = { messages: [
   ...pair('discovery', 'bash', {command:'git status --short'}),
   ...pair('test', 'bash', {command:'pytest tests/'}),
   ...pair('status-patch', 'bash', {command:'git status -vv'}),
   ...pair('log-patch', 'bash', {command:'git log -p'}),
   ...pair('combined-patch', 'bash', {command:'git log -c'}),
   ...pair('find-exec', 'bash', {command:'find . -execdir script {} +'}),
   ...pair('find-write', 'bash', {command:'find . -fls output'}),
   ...pair('diff', 'bash', {command:'git diff'}),
   ...pair('read', 'read', {path:'source.py'}),
   ...pair('edit', 'edit', {path:'source.py'}),
   ...pair('failure', 'bash', {command:'git status'}, true),
   ...pair('compound', 'bash', {command:'ls; pytest'}),
   ...pair('mutation', 'bash', {command:'find . -delete'}),
 ] };
 const before = structuredClone(event);
 const first = await invoke('context', event);
 assert.deepEqual(event, before, 'native messages must remain byte-identical');
 assert.ok(first.messages[1].content[0].text.includes('headroom_retrieve'));
 for (let i=3;i<event.messages.length;i+=2) assert.deepEqual(first.messages[i], event.messages[i]);
 const calls = readFileSync(join(temporary, 'calls'), 'utf8');
 const second = await invoke('context', event);
 assert.deepEqual(second, first, 'already-sent prefix must remain stable');
 assert.equal(readFileSync(join(temporary, 'calls'), 'utf8'), calls, 'no repeated compression');
 process.env.MEGAI_HEADROOM = '0';
 assert.equal(await invoke('context', event), undefined);
 delete process.env.MEGAI_HEADROOM;
 await invoke('session_start');
 rmSync(binary);
 const failed = await invoke('context', event);
 assert.deepEqual(failed.messages, event.messages, 'missing runtime must preserve all originals');
 assert.equal(notices.length, 1);
 assert.deepEqual(ctx.model, {id:'preserve-model',provider:'openai-codex'});
 assert.equal(ctx.thinkingLevel, 'high');
 assert.deepEqual([...extension.tools.keys()].sort(), ['headroom_memory','headroom_retrieve']);
 await invoke('session_shutdown');
 const { activation } = await import(pathToFileURL(resolve('lib/verify_headroom_activation.mjs')));
 const agentDir = join(temporary, 'activation-agent');
 mkdirSync(join(agentDir, 'extensions/megai-headroom'), { recursive: true });
 copyFileSync(resolve('pi-skill/headroom/index.ts'), join(agentDir, 'extensions/megai-headroom/index.ts'));
 assert.equal(await activation(packageRoot, { cwd: temporary, agentDir,
   noSkills: true, settingsManager: SettingsManager.inMemory({ packages: [] }) }), true);
 assert.equal(await activation(packageRoot, { cwd: temporary, agentDir,
   noSkills: true, settingsManager: SettingsManager.inMemory({ packages: [], extensions: ['-' + join(agentDir, 'extensions/megai-headroom/index.ts')] }) }), false);
 mkdirSync(join(temporary, 'lib'), { recursive: true });
 for (const name of ['verify_headroom_activation.mjs', 'verify_headroom_activation.sh']) {
   copyFileSync(resolve('lib', name), join(temporary, 'lib', name));
 }
 const canary = join(temporary, 'canary-loaded');
 writeFileSync(join(agentDir, 'extensions/credential-canary.ts'), `
 import { writeFileSync } from 'node:fs';
 if (process.env.OPENAI_API_KEY || process.env.NODE_OPTIONS || process.env.PYTHONPATH) throw new Error('credential canary leaked');
 writeFileSync(${JSON.stringify(canary)}, 'loaded without credentials');
 setInterval(() => {}, 1000); // Actual user extensions can leave loader-time timers.
 export default function(pi) {}
 `);
 mkdirSync(join(temporary, 'bin'));
 const piBin = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8')).bin.pi;
 symlinkSync(join(packageRoot, piBin), join(temporary, 'bin/pi'));
 const verification = spawnSync('bash', [join(temporary, 'lib/verify_headroom_activation.sh')], {
   cwd: temporary, encoding: 'utf8', timeout: 30000,
   env: { ...process.env, HOME: temporary, PI_CODING_AGENT_DIR: agentDir,
     PI_PACKAGE_ROOT: '', PATH: join(temporary, 'bin') + ':' + process.env.PATH,
     OPENAI_API_KEY: 'synthetic-only', NODE_OPTIONS: '--no-warnings', PYTHONPATH: '/synthetic' },
 });
 assert.equal(verification.status, 0, verification.stdout + verification.stderr);
 assert.equal(readFileSync(canary, 'utf8'), 'loaded without credentials');
 console.log('PASS: actual Pi loader; immutable sessions, raw patches, stable prefix, opt-out/inactive detection, failure fallback, bridge and custom-extension auth isolation');
} finally {
 if (originalRoot === undefined) delete process.env.MEGAI_HOME; else process.env.MEGAI_HOME = originalRoot;
 rmSync(temporary, { recursive: true, force: true });
}
