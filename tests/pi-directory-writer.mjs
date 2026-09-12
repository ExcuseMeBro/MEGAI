// Native Pi regression: explicit scoped non-Git config writers, no live agents.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, realpathSync, symlinkSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = realpathSync(mkdtempSync(join(tmpdir(), 'directory-writer-')));
const previous = process.env.PASEO_HOME;
try {
  const root = join(temp, 'umbrella'), scope = join(root, 'infra');
  mkdirSync(scope, { recursive: true });
  const home = join(temp, 'paseo'); mkdirSync(join(home, 'projects'), { recursive: true });
  process.env.PASEO_HOME = home;
  writeFileSync(join(home, 'projects/projects.json'), JSON.stringify([{ projectId: 'prj-dir', kind: 'non_git', rootPath: root }]));
  writeFileSync(join(home, 'projects/workspaces.json'), JSON.stringify([{workspaceId:'wks-dir', projectId:'prj-dir', cwd:root, kind:'directory', isPaseoOwnedWorktree:false, worktreeRoot:null}]));
  const loader = new DefaultResourceLoader({ cwd: root, agentDir: join(temp, 'agent'),
    settingsManager: SettingsManager.inMemory({packages:[]}), additionalExtensionPaths:[resolve('pi-skill/workspace-guard/index.ts')] });
  await loader.reload(); const loaded = loader.getExtensions(); assert.deepEqual(loaded.errors, []);
  assert.equal(loaded.extensions.length, 1);
  let cases = 0;
  const agent = {workspaceId:'wks-dir', provider:'pi/existing-model', labels:{'megai.access':'write','megai.writeScope':'infra'}};
  const check = async (input, expected) => {
    const original = structuredClone(input); let result;
    for (const hook of loaded.extensions[0].handlers.get('tool_call')) result = await hook({toolName:'paseo_create_agent',input},{cwd:root});
    assert.equal(Boolean(result?.block), expected, `scoped non-Git config writer must launch: ${JSON.stringify(input)}: ${result?.reason}`);
    assert.deepEqual(input, original); cases++;
  };
  await check(agent, false);
  await check({...agent, labels:{...agent.labels,'megai.writeScope':'.'}}, false);
  for (const value of ['', '..', '../outside', '/tmp', 'infra/../infra', 'missing', 3]) {
    await check({...agent, labels:{...agent.labels,'megai.writeScope':value}}, true);
  }
  await check({...agent, labels:{'megai.access':'write'}}, true);
  await check({...agent, labels:{...agent.labels,'megai.access':'unknown'}}, true);
  await check({...agent, provider:'codex/model'}, true);
  await check({...agent, workspaceId:'unknown'}, true);
  symlinkSync(scope, join(root,'alias'));
  await check({...agent, labels:{...agent.labels,'megai.writeScope':'alias'}}, true);
  writeFileSync(join(scope,'.git'), 'gitdir: /missing/broken\n'); await check(agent,true); rmSync(join(scope,'.git'));
  execFileSync('git',['-C',scope,'init','-q']); await check(agent,false);
  rmSync(join(scope,'.git'),{recursive:true});
  await check(agent,false);
  await check({...agent, labels:{'megai.access':'read-only'}}, false);
  console.log(`PASS: ${cases} scoped-directory writer launch cases; inputs unchanged; no agent or registry mutations.`);
} finally {
  if (previous === undefined) delete process.env.PASEO_HOME; else process.env.PASEO_HOME=previous;
  rmSync(temp,{recursive:true,force:true});
}
