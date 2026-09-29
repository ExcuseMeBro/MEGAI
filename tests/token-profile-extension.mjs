// Real Pi loader/hooks for the opt-in token profile: profile present/missing/malformed,
// explicit overrides, unchanged raw messages, RTK bypass and single core discovery.
// Offline; the bridge is a local fixture and no provider is contacted.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';

const packageRoot = process.env.PI_PACKAGE_ROOT;
assert.ok(packageRoot, 'Set PI_PACKAGE_ROOT to the installed @earendil-works/pi-coding-agent directory');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')));

const temporary = mkdtempSync(join(tmpdir(), 'token-profile-extension-'));
const agentDir = join(temporary, 'agent');
mkdirSync(agentDir, { recursive: true });
const original = {
  HOME: process.env.HOME,
  MEGAI_HOME: process.env.MEGAI_HOME,
  PI_CODING_AGENT_DIR: process.env.PI_CODING_AGENT_DIR,
  MEGAI_HEADROOM_VERBOSITY: process.env.MEGAI_HEADROOM_VERBOSITY,
};
process.env.HOME = temporary; // Isolate ~/.agents/skills and ~/.pi/agent discovery.
process.env.MEGAI_HOME = temporary;
process.env.PI_CODING_AGENT_DIR = agentDir;
process.env.PI_OFFLINE = '1';
delete process.env.MEGAI_HEADROOM_VERBOSITY;

const profilePath = join(agentDir, 'megai-token-profile.json');
const calls = () => { try { return readFileSync(join(temporary, 'calls'), 'utf8'); } catch { return ''; } };
const clearCalls = () => rmSync(join(temporary, 'calls'), { force: true });

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
 q.action==='compress' ? {text:'compact fixture',compressed:true,id:'123456789abcdef123456789'} : {memories:[]};
 process.stdout.write(JSON.stringify(r));
});
`, { mode: 0o700 });

try {
  for (const skill of ['caveman']) {
    mkdirSync(join(agentDir, 'skills', skill), { recursive: true });
    for (const name of ['SKILL.md', 'LICENSE.md']) {
      writeFileSync(join(agentDir, 'skills', skill, name),
        readFileSync(resolve('pi-skill/token-profile', skill, name)));
    }
  }
  const skillLoader = (settings) => new DefaultResourceLoader({ cwd: temporary, agentDir,
    settingsManager: SettingsManager.inMemory({ packages: [], ...settings }) });
  const discovery = skillLoader({});
  await discovery.reload();
  const skills = discovery.getSkills();
  assert.deepEqual(skills.diagnostics, []);
  assert.deepEqual(skills.skills.map(s => s.name).sort(), ['caveman'], 'each core exactly once');
  assert.equal(skills.skills.filter(s => s.filePath.endsWith('LICENSE.md')).length, 0, 'license is not a skill');
  for (const skill of skills.skills) assert.ok(skill.filePath.startsWith(agentDir), skill.filePath);
  // Existing user exclusions must win; the installer reports gaps instead of clobbering them.
  const filtered = skillLoader({ skills: ['!' + join(agentDir, 'skills/caveman') + '/**'] });
  await filtered.reload();
  assert.deepEqual(filtered.getSkills().skills.map(s => s.name), []);

  const loader = new DefaultResourceLoader({ cwd: temporary, agentDir,
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [resolve('pi-skill/headroom/index.ts')] });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  const extension = loaded.extensions[0];
  const notices = [];
  const ctx = { cwd: temporary, hasUI: true, ui: { notify: (text, type) => notices.push(`${type}:${text}`) },
    model: { id: 'preserve-model', provider: 'openai-codex' }, thinkingLevel: 'high' };
  const invoke = async (name, event = {}) => {
    let result;
    for (const handler of extension.handlers.get(name) || []) result = await handler(event, ctx);
    return result;
  };
  const start = async () => { clearCalls(); notices.length = 0; await invoke('session_start'); };

  // Missing profile keeps the existing default steering untouched.
  rmSync(profilePath, { force: true });
  await start();
  let shaped = await invoke('before_agent_start', { systemPrompt: 'unchanged policy' });
  assert.ok(shaped.systemPrompt.includes('Headroom concise fixture'));
  assert.equal(calls(), 'steering\n');

  // Max profile hands chat terseness to Caveman and drops only the duplicate steering.
  writeFileSync(profilePath, '{"schema":1,"profile":"max"}\n');
  await start();
  assert.equal(await invoke('before_agent_start', { systemPrompt: 'unchanged policy' }), undefined);
  assert.equal(calls(), '');

  const raw = 'synthetic original '.repeat(300);
  const pair = (id, name, args, isError = false) => [
    { role: 'assistant', content: [{ type: 'toolCall', id, name, arguments: args }] },
    { role: 'toolResult', toolCallId: id, toolName: name, isError, content: [{ type: 'text', text: raw }], timestamp: 1 },
  ];
  const event = { messages: [
    ...pair('discovery', 'bash', { command: 'git status --short' }),
    ...pair('rtk-ls', 'bash', { command: 'rtk ls' }),
    ...pair('rtk-status', 'bash', { command: 'rtk git status' }),
    ...pair('rtk-log', 'bash', { command: 'rtk git log' }),
    ...pair('rtk-read', 'bash', { command: 'rtk read source.py' }),
    ...pair('rtk-test', 'bash', { command: 'rtk test' }),
    ...pair('rtk-diff', 'bash', { command: 'rtk diff' }),
  ] };
  const before = structuredClone(event);
  const first = await invoke('context', event);
  assert.deepEqual(event, before, 'native messages must remain byte-identical');
  assert.ok(first.messages[1].content[0].text.includes('headroom_retrieve'));
  for (let i = 3; i < event.messages.length; i += 2) {
    assert.deepEqual(first.messages[i], event.messages[i], 'RTK output must bypass Headroom');
  }
  const second = await invoke('context', event);
  assert.deepEqual(second, first, 'already-sent prefix must remain stable');
  assert.equal(calls(), 'compress\n', 'compression still runs under the max profile');

  // Explicit environment and command overrides always win over the profile.
  process.env.MEGAI_HEADROOM_VERBOSITY = '2';
  await start();
  shaped = await invoke('before_agent_start', { systemPrompt: 'unchanged policy' });
  assert.ok(shaped.systemPrompt.includes('Headroom concise fixture'));
  delete process.env.MEGAI_HEADROOM_VERBOSITY;
  await start();
  const command = extension.commands.get('headroom-verbosity');
  assert.ok(command, 'existing verbosity command must remain registered');
  await command.handler('3', ctx);
  shaped = await invoke('before_agent_start', { systemPrompt: 'unchanged policy' });
  assert.ok(shaped.systemPrompt.includes('Headroom concise fixture'));

  // Malformed profiles warn once and keep the safe baseline.
  for (const value of ['{not json', '{"schema":2,"profile":"max"}\n']) {
    writeFileSync(profilePath, value);
    await start();
    shaped = await invoke('before_agent_start', { systemPrompt: 'unchanged policy' });
    assert.ok(shaped.systemPrompt.includes('Headroom concise fixture'));
    assert.equal(notices.length, 1);
    assert.match(notices[0], /Token profile unreadable/);
  }

  assert.deepEqual(ctx.model, { id: 'preserve-model', provider: 'openai-codex' });
  assert.equal(ctx.thinkingLevel, 'high');
  assert.equal(extension.handlers.has('before_provider_request'), false);
  assert.equal(extension.handlers.has('before_provider_headers'), false);

  // Real activation verifier: an owned max profile passes; unowned/foreign legacy still blocks.
  const { activation } = await import(pathToFileURL(resolve('lib/verify_headroom_activation.mjs')));
  const activationAgent = join(temporary, 'activation-agent');
  mkdirSync(join(activationAgent, 'extensions/megai-headroom'), { recursive: true });
  writeFileSync(join(activationAgent, 'extensions/megai-headroom/index.ts'),
    readFileSync(resolve('pi-skill/headroom/index.ts')));
  for (const skill of ['caveman']) {
    mkdirSync(join(activationAgent, 'skills', skill), { recursive: true });
    writeFileSync(join(activationAgent, 'skills', skill, 'SKILL.md'),
      readFileSync(resolve('pi-skill/token-profile', skill, 'SKILL.md')));
  }
  writeFileSync(join(activationAgent, 'megai-token-profile.json'), '{"schema":1,"profile":"max"}\n');
  const sidecar = join(activationAgent, 'megai-token-profile.json');
  const receiptPath = join(temporary, 'slim-wiring.json');
  const ownedReceipt = {};
  for (const skill of ['caveman']) {
    const file = join(activationAgent, 'skills', skill, 'SKILL.md');
    ownedReceipt[file] = createHash('sha256').update(readFileSync(file)).digest('hex');
  }
  ownedReceipt[sidecar] = createHash('sha256').update(readFileSync(sidecar)).digest('hex');
  writeFileSync(receiptPath, JSON.stringify(ownedReceipt));
  const activationOptions = { cwd: temporary, agentDir: activationAgent,
    settingsManager: SettingsManager.inMemory({ packages: [] }) };
  assert.equal(await activation(packageRoot, activationOptions), true,
    'owned max profile must pass activation verification');
  const settingsActivation = (settings) => activation(packageRoot,
    { cwd: temporary, agentDir: activationAgent, settingsManager: SettingsManager.inMemory({ packages: [], ...settings }) });
  // Native override semantics: `!name` matches the parent skill name, plain paths are
  // additive, and `-name` is exact-path-only so it does not disable a core.
  await assert.rejects(settingsActivation({ skills: ['!caveman'] }), /Token profile core not active/);
  await assert.rejects(settingsActivation({ skills: ['!' + join(activationAgent, 'skills/caveman') + '/**'] }), /Token profile core not active/);
  assert.equal(await settingsActivation({ skills: ['-caveman'] }), true, '-caveman is exact-path-only in native Pi');
  assert.equal(await settingsActivation({ skills: ['/opt/shared/skills/caveman/SKILL.md'] }), true, 'positive skill paths are additive');
  assert.equal(await settingsActivation({
    extensions: ['-' + join(activationAgent, 'extensions/megai-headroom/index.ts')] }), false, 'excluded Headroom is not active');
  // Sidecar receipt removed: the cores stay receipted but the profile is not owned.
  const withoutSidecar = { ...ownedReceipt };
  delete withoutSidecar[sidecar];
  writeFileSync(receiptPath, JSON.stringify(withoutSidecar));
  await assert.rejects(activation(packageRoot, activationOptions), /Retired Pi resources/);
  // Sidecar receipt modified: the sidecar hash must match its receipt.
  writeFileSync(receiptPath, JSON.stringify({ ...ownedReceipt, [sidecar]: '0'.repeat(64) }));
  await assert.rejects(activation(packageRoot, activationOptions), /Retired Pi resources/);
  // Unowned core receipts no longer exempt the local cores.
  writeFileSync(receiptPath, '{}');
  await assert.rejects(activation(packageRoot, activationOptions), /Retired Pi resources/);
  const foreign = join(temporary, '.agents/skills/legacy/caveman');
  mkdirSync(foreign, { recursive: true });
  writeFileSync(join(foreign, 'SKILL.md'),
    '---\nname: legacy-caveman-core\ndescription: foreign legacy fixture\n---\nbody\n');
  writeFileSync(receiptPath, JSON.stringify(ownedReceipt));
  await assert.rejects(activation(packageRoot, activationOptions), /Retired Pi resources/);
  rmSync(join(temporary, '.agents'), { recursive: true, force: true });
  console.log('PASS: real Pi loader; profile present/missing/malformed, explicit overrides, raw RTK bypass, single core discovery, owned-profile activation vs foreign legacy');
} finally {
  for (const [key, value] of Object.entries(original)) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  }
  rmSync(temporary, { recursive: true, force: true });
}
