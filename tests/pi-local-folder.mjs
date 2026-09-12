// Folder-first policy: native hook + real Git; no live Paseo writes or agents.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, realpathSync, symlinkSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT, 'dist/index.js')));
const temp = realpathSync(mkdtempSync(join(tmpdir(), 'local-folder-')));
const oldHome = process.env.PASEO_HOME;
try {
  const root = join(temp, 'umbrella'), repo = join(temp, 'repo'), child = join(root, 'component');
  const home = join(temp, 'paseo');
  for (const path of [child, repo, join(home, 'projects')]) mkdirSync(path, {recursive:true});
  for (const path of [repo, child]) execFileSync('git', ['-C', path, 'init', '-q']);
  process.env.PASEO_HOME = home;
  const projects = [{projectId:'umbrella',rootPath:root,kind:'non_git'}, {projectId:'repo',rootPath:repo,kind:'git'}];
  const workspaces = [
    {workspaceId:'local-dir',projectId:'umbrella',cwd:root,kind:'directory',isPaseoOwnedWorktree:false,worktreeRoot:null},
    {workspaceId:'local-git',projectId:'repo',cwd:repo,kind:'local_checkout',isPaseoOwnedWorktree:false,worktreeRoot:repo},
  ];
  const save = (name, rows) => writeFileSync(join(home, 'projects', name+'.json'), JSON.stringify(rows));
  save('projects', projects); save('workspaces', workspaces);
  const bytes = readFileSync(join(home,'projects/projects.json'));
  const loader = new DefaultResourceLoader({cwd:root,agentDir:join(temp,'agent'),settingsManager:SettingsManager.inMemory({packages:[]}),additionalExtensionPaths:[process.env.MEGAI_TEST_GUARD || resolve('pi-skill/workspace-guard/index.ts')]});
  await loader.reload(); const loaded = loader.getExtensions(); assert.deepEqual(loaded.errors,[]);
  assert.equal(loaded.extensions.length,1); let cases=0;
  const check = async (toolName,input,blocked,cwd=root) => {
    const before=structuredClone(input); let result;
    for (const hook of loaded.extensions[0].handlers.get('tool_call')) result=await hook({toolName,input},{cwd});
    assert.equal(Boolean(result?.block),blocked,`folder-first local workspace must work without task branch: ${toolName} ${JSON.stringify(input)}: ${result?.reason}`);
    assert.deepEqual(input,before); cases++;
  };
  const create = {isolation:'local',projectId:'repo',path:repo};
  const agent = {workspaceId:'local-git',provider:'pi/existing-model',labels:{'megai.access':'write','megai.writeScope':'.'}};
  await check('paseo_create_workspace',create,false,repo);
  await check('paseo_create_workspace',{isolation:'local',projectId:'repo'},false,repo);
  await check('paseo_create_agent',agent,false,repo);
  await check('mcp',{tool:'paseo_create_agent',args:JSON.stringify(agent)},false,repo);
  await check('paseo_create_agent',{...agent,labels:{'megai.access':'read-only'}},false,repo);
  for (const patch of [{branchName:'task'}, {baseBranch:'main'}, {mode:'branch-off'}, {worktreeSlug:'task'}, {branch:'main'}, {prNumber:1}, {forge:'github'}, {path:root}, {projectId:'umbrella'}]) await check('paseo_create_workspace',{...create,...patch},true,repo);
  for (const patch of [{workspaceId:'local-dir'}, {provider:'codex/model'}, {labels:{}}, {labels:{'megai.access':'write'}}, {labels:{'megai.access':'write','megai.writeScope':'../umbrella'}}, {workspaceId:'missing'}]) await check('paseo_create_agent',{...agent,...patch},true,repo);
  const dirAgent={...agent,workspaceId:'local-dir',labels:{'megai.access':'write','megai.writeScope':'component'}};
  await check('paseo_create_agent',dirAgent,false);
  await check('paseo_create_agent',dirAgent,false,child);
  await check('paseo_create_workspace',{isolation:'local',projectId:'umbrella'},false,child);
  await check('paseo_create_agent',{...dirAgent,labels:{'megai.access':'write','megai.writeScope':'.'}},false);
  symlinkSync(repo,join(root,'escape'));
  await check('paseo_create_agent',{...dirAgent,labels:{'megai.access':'write','megai.writeScope':'escape'}},true);
  await check('paseo_create_workspace',{isolation:'local',projectId:'umbrella',path:join(root,'escape')},true);
  for (const patch of [{archivedAt:'2026-01-01'}, {cwd:root}, {isPaseoOwnedWorktree:true}, {worktreeRoot:root}, {kind:'unknown'}]) {
    save('workspaces',[workspaces[0],{...workspaces[1],...patch}]); await check('paseo_create_agent',agent,true,repo);
  }
  save('workspaces',workspaces);
  save('projects',[...projects,{...projects[1],projectId:'duplicate'}]); await check('paseo_create_workspace',create,true,repo);
  save('projects',projects);
  const cli=process.env.MEGAI_TEST_IDENTITY || resolve('pi-skill/workspace-guard/identity.mjs');
  const result=spawnSync(process.execPath,[cli,'--root',child],{encoding:'utf8',timeout:10000});
  assert.equal(result.status,0,result.stderr); assert.equal(JSON.parse(result.stdout).projectId,'umbrella');
  assert.equal(JSON.parse(result.stdout).root,root);
  mkdirSync(join(root,'broken')); writeFileSync(join(root,'broken/.git'),'gitdir: /missing\n');
  await check('paseo_create_agent',{...dirAgent,labels:{'megai.access':'write','megai.writeScope':'broken'}},true);
  await check('paseo_create_workspace',{isolation:'local',projectId:'umbrella'},true,join(root,'broken'));
  await check('paseo_create_project',{path:child},true,child);
  assert.deepEqual(readFileSync(join(home,'projects/projects.json')),bytes);
  assert.deepEqual(JSON.parse(readFileSync(join(home,'projects/workspaces.json'))),workspaces);
  assert.equal(execFileSync('git',['-C',repo,'for-each-ref','refs/heads'],{encoding:'utf8'}),'');
  console.log(`PASS: ${cases} native local-folder cases + nested-repository identity CLI; no project/branch/agent/registry mutation.`);
} finally {
  if(oldHome===undefined) delete process.env.PASEO_HOME; else process.env.PASEO_HOME=oldHome;
  rmSync(temp,{recursive:true,force:true});
}
