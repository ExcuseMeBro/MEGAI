// Explicit end-to-end Pi + installed Headroom runtime. Disposable storage; no model/provider calls.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, cpSync, symlinkSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const installed = process.env.HEADROOM_INSTALL_ROOT;
const packageRoot = process.env.PI_PACKAGE_ROOT;
assert.ok(installed && packageRoot, 'Set HEADROOM_INSTALL_ROOT and PI_PACKAGE_ROOT explicitly');
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')));
const temporary = mkdtempSync(join(tmpdir(), 'headroom-e2e-'));
const previous = process.env.MEGAI_HOME;
process.env.MEGAI_HOME = temporary;
process.env.PI_OFFLINE = '1';
try {
  mkdirSync(join(temporary, 'venv'));
  mkdirSync(join(temporary, 'pi-skill'));
  mkdirSync(join(temporary, 'project'));
  symlinkSync(join(installed, 'venv/headroom'), join(temporary, 'venv/headroom'));
  symlinkSync(join(installed, 'headroom-assets'), join(temporary, 'headroom-assets'));
  cpSync(join(installed, 'pi-skill/headroom'), join(temporary, 'pi-skill/headroom'), { recursive: true });
  const cwd = join(temporary, 'project');
  const loader = new DefaultResourceLoader({ cwd, agentDir: join(temporary, 'agent'), noSkills: true,
    settingsManager: SettingsManager.inMemory({ packages: [] }),
    additionalExtensionPaths: [join(installed, 'pi-skill/headroom/index.ts')] });
  await loader.reload();
  assert.deepEqual(loader.getExtensions().errors, []);
  const extension = loader.getExtensions().extensions[0];
  const ctx = { cwd, hasUI: false, model: { id: 'unchanged', provider: 'unchanged' } };
  async function invoke(name, event = {}) {
    let value;
    for (const handler of extension.handlers.get(name) || []) value = await handler(event, ctx);
    return value;
  }
  async function tool(name, params) {
    const result = await extension.tools.get(name).definition.execute('fixture', params, undefined, undefined, ctx);
    return JSON.parse(result.content[0].text);
  }
  await invoke('session_start');
  const shaped = await invoke('before_agent_start', { systemPrompt: 'Original policy.' });
  assert.ok(shaped.systemPrompt.startsWith('Original policy.'));
  const original = JSON.stringify(Array.from({ length: 300 }, (_, id) => ({ id, status: 'ok', message: 'successful synthetic discovery', value: 100 })));
  const messages = [
    { role: 'assistant', content: [{ type: 'toolCall', id: 'discovery', name: 'bash', arguments: { command: 'git status --short' } }] },
    { role: 'toolResult', toolCallId: 'discovery', toolName: 'bash', isError: false, content: [{ type: 'text', text: original }], timestamp: 1 },
  ];
  const before = structuredClone(messages);
  const compressed = await invoke('context', { messages });
  assert.deepEqual(messages, before);
  const id = compressed.messages[1].content[0].text.match(/headroom_retrieve id=([a-f0-9]+)/)?.[1];
  assert.ok(id, 'actual Headroom compression must produce a verified retrieval marker');
  let offset = 0;
  const pages = [];
  do {
    const page = await tool('headroom_retrieve', { id, offset, limit: 8000 });
    pages.push(page.text); offset = page.next_offset;
  } while (offset !== null);
  assert.equal(pages.join(''), original);
  const text = 'Synthetic acceptance fixture: release must remain on the approved task branch.';
  const saved = await tool('headroom_memory', { action: 'save', text });
  const recalled = await tool('headroom_memory', { action: 'recall', text: 'Which branch is approved for release?' });
  assert.ok(recalled.memories.some(memory => memory.id === saved.id));
  assert.equal((await tool('headroom_memory', { action: 'save', text })).id, saved.id);
  assert.deepEqual(ctx.model, { id: 'unchanged', provider: 'unchanged' });
  await invoke('session_shutdown');
  console.log('PASS: installed runtime + actual Pi hooks/tools; compression, exact paginated retrieval, semantic memory, idempotent retry, immutable native messages. No provider calls.');
} finally {
  if (previous === undefined) delete process.env.MEGAI_HOME; else process.env.MEGAI_HOME = previous;
  rmSync(temporary, { recursive: true, force: true });
}
