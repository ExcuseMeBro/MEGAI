// Task-specific local acceptance: read-only checks of the user's installed Pi resources.
// This is deliberately not part of the portable default test suite.
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const home = homedir();
const agentDir = join(home, '.pi/agent');
const piLoader = join(home, '.bun/install/global/node_modules/@earendil-works/pi-coding-agent/dist/core/resource-loader.js');
assert.ok(existsSync(piLoader), 'installed Pi resource loader must exist');
const { DefaultResourceLoader } = await import(pathToFileURL(piLoader).href);
const loader = new DefaultResourceLoader({ cwd: process.cwd(), agentDir });
await loader.reload();
const prompts = loader.getPrompts().prompts.map(({ name }) => name);
assert.ok(prompts.includes('mdev') && prompts.includes('prdev'), 'preserve delivery prompts');
assert.ok(!prompts.includes('splane'), 'retired prompt must not load');
const extensions = loader.getExtensions().extensions;
assert.ok(extensions.every((extension) => !extension.commands?.has?.('splane')),
  'retired extension command must not load');

const retired = '/splane';
for (const path of [
  join(agentDir, 'AGENTS.md'), join(home, '.codex/AGENTS.md'),
  join(agentDir, 'prompts/mdev.md'), join(agentDir, 'prompts/prdev.md'),
]) {
  assert.doesNotMatch(readFileSync(path, 'utf8'), /\/splane/i, `stale guidance in ${path}`);
}
const settings = JSON.parse(readFileSync(join(agentDir, 'settings.json'), 'utf8'));
assert.ok(!JSON.stringify(settings).includes(retired), 'settings must not select retired prompt');
for (const path of [
  join(agentDir, 'prompts/splane.md'),
  join(home, '.megai/lib/pellet_plane_bisync.py'),
  join(home, '.config/megai/pellet-plane-bisync.json'),
  join(home, '.config/megai/pellet-plane-bisync.lock'),
  join(home, '.config/megai/pellet-plane-sync.json'),
]) assert.ok(!existsSync(path), `dedicated sync asset still active: ${path}`);
console.log(JSON.stringify({ result: 'PASS', loadedPrompts: prompts, retiredSyncAssetsAbsent: true }));
