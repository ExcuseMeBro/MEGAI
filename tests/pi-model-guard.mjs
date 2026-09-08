// Actual Pi loader and tool_call hooks, offline: no agent/provider is invoked.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

assert.ok(process.env.PI_PACKAGE_ROOT, 'Set PI_PACKAGE_ROOT to installed Pi');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = mkdtempSync(join(tmpdir(), 'pi-model-guard-'));
try {
  process.env.PI_OFFLINE = '1';
  const liveDir = process.env.MEGAI_GUARD_AGENT_DIR;
  const loader = new DefaultResourceLoader(liveDir ? { cwd: temp, agentDir: liveDir } : {
    cwd: temp, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [resolve('pi-skill/model-guard/index.ts')],
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  if (!liveDir) assert.equal(loaded.extensions.length, 1);
  const extension = loaded.extensions.find(ext => /(?:model-guard)[/\\]index\.ts$/.test(ext.resolvedPath));
  assert.ok(extension, 'Model guard is inactive in actual Pi resource selection');
  assert.ok(extension.handlers.has('tool_call'), 'Missing model enforcement hook');
  const check = async (toolName, input, blocked) => {
    const before = structuredClone(input);
    let result;
    for (const hook of extension.handlers.get('tool_call')) result = await hook({ toolName, input }, {});
    assert.equal(Boolean(result?.block), blocked, `${toolName}: ${JSON.stringify(input)}`);
    assert.deepEqual(input, before, 'Never silently rewrite model/thinking/task');
  };
  const args = model => ({ provider: `pi/openai-codex/${model}`, settings: { thinkingOptionId: 'high' }, initialPrompt: 'synthetic' });
  const models = ['gpt-6-astra', 'gpt-5.6-luna', 'gpt-5.6-sol', 'gpt-5.6-terra'];
  for (const model of models) {
    for (const thinkingOptionId of ['medium', 'high']) {
      const input = { ...args(model), settings: { thinkingOptionId } };
      await check('paseo_create_agent', input, false);
      await check('mcp', { tool: 'paseo_create_agent', args: input }, false);
      await check('mcp', { server: 'paseo', tool: 'create_agent', args: JSON.stringify(input) }, false);
      await check('mcp__paseo', { tool: 'create_agent', args: input }, false);
    }
  }
  for (const model of ['gpt-5.4', 'gpt-5.5', 'gpt-5.4-mini', 'gpt-6-astra-preview', 'gpt-*', 'claude-sonnet-4-6', 'MiniMax-M2.5']) {
    await check('mcp', { tool: 'paseo_create_agent', args: args(model) }, true);
  }
  for (const input of [{}, { provider: 'pi' }, { ...args(models[0]), provider: 'codex/gpt-6-astra' },
    { ...args(models[0]), provider: 'pi/openai/gpt-6-astra' }, { ...args(models[0]), settings: {} },
    { ...args(models[0]), settings: { thinkingOptionId: 'low' } }]) {
    await check('mcp__paseo', { tool: 'create_agent', args: input }, true);
  }
  await check('mcp', { tool: 'paseo-create-agent', args: args('gpt-5.4') }, true);
  await check('mcp', { tool: 'create_agent', args: args('gpt-5.4') }, true);
  await check('create_agent', args('gpt-5.4'), true);
  await check('mcp__paseo', { tool: 'create-agent', args: args('gpt-5.4') }, true);
  await check('mcp', { tool: 'paseo/create_agent', args: '{bad' }, true);
  await check('mcp', { tool: 'paseo_create_agent', args: 'null' }, true);
  await check('mcp', { tool: 'paseo_create_agent', args: args(models[0]), action: 'ui-messages' }, false);
  for (const model of models) await check('paseo_update_agent', { settings: { model: `openai-codex/${model}`, thinkingOptionId: 'high' } }, false);
  for (const model of [null, '', 'gpt-5.4', 'openai-codex/gpt-5.4']) await check('paseo_update_agent', { settings: { model } }, true);
  await check('paseo_update_agent', { settings: { model: 'openai-codex/gpt-5.6-luna' } }, true);
  await check('paseo_update_agent', { name: 'rename only' }, false);
  await check('paseo_update_agent', { settings: { thinkingOptionId: null } }, true);
  for (const name of ['subagent', 'subagents', 'dispatch_agent', 'paseo_create_schedule', 'paseo_update_schedule', 'paseo_resume_schedule', 'paseo_run_schedule_once']) await check(name, {}, true);
  await check('mcpScript', { code: 'await tools.paseo.create_agent({})' }, true);
  await check('bash', { command: 'paseo run --provider pi --model openai-codex/gpt-5.4 task' }, true);
  await check('bash', { command: 'paseo --json run task' }, true);
  await check('bash', { command: 'pi --model gpt-5.4 -p task' }, true);
  await check('bash', { command: 'pi -p task' }, true);
  for (const [name, input] of [['bash', { command: 'git diff' }], ['bash', { command: 'paseo --help' }],
    ['read', { path: 'paseo.ts' }], ['mcp', { tool: 'plane_workitem', args: { action: 'create' } }],
    ['mcp', { search: 'paseo create_agent' }], ['paseo_list_models', { provider: 'pi' }]]) await check(name, input, false);
  assert.equal(extension.handlers.has('before_provider_request'), false);
  console.log('PASS: four exact models, medium/high, MCP direct/proxy/namespace/JSON, fail-closed missing/invalid routes, updates and alternate launches; arguments unchanged');
} finally { rmSync(temp, { recursive: true, force: true }); }
// Installed third-party extensions may leave factory-time timers. This process
// is an offline loader snapshot, not a running Pi session.
if (process.env.MEGAI_GUARD_AGENT_DIR) process.exit(0);
