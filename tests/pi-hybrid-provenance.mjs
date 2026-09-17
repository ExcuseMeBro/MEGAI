// Regression for native managed-workspace provenance; only disposable Git/registry data.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, realpathSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { pathToFileURL } from 'node:url';
const { DefaultResourceLoader, SettingsManager }=await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT,'dist/index.js')));
const temp=realpathSync(mkdtempSync(join(tmpdir(),'hybrid-provenance-'))),previous=process.env.PASEO_HOME;
try{
 const root=join(temp,'umbrella'),repo=join(root,'backend'),home=join(temp,'paseo'),tree=join(home,'worktrees/backend/task');
 mkdirSync(repo,{recursive:true});mkdirSync(join(home,'projects'),{recursive:true});process.env.PASEO_HOME=home;
 const git=(...args)=>execFileSync('git',['-C',repo,...args],{stdio:'pipe'});
 git('init','-q','-b','dev');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','base','--allow-empty');git('worktree','add','-qb','task/task',tree);
 writeFileSync(join(home,'projects/projects.json'),JSON.stringify([{projectId:'umbrella',rootPath:root,kind:'non_git'}]));
 const row={workspaceId:'task',projectId:'umbrella',cwd:tree,kind:'worktree',isPaseoOwnedWorktree:true,worktreeRoot:tree};
 const loader=new DefaultResourceLoader({cwd:root,agentDir:join(temp,'agent'),settingsManager:SettingsManager.inMemory({packages:[]}),additionalExtensionPaths:[resolve('pi-skill/workspace-guard/index.ts')]});
 await loader.reload();const loaded=loader.getExtensions();assert.deepEqual(loaded.errors,[]);assert.equal(loaded.extensions.length,1);
 let cases=0;
 for(const [patch,expected] of [[{},true],[{mainRepoRoot:null},true],[{mainRepoRoot:3},true],[{mainRepoRoot:root},true],[{mainRepoRoot:repo},false]]){
  writeFileSync(join(home,'projects/workspaces.json'),JSON.stringify([{...row,...patch}]));let result;
  const input={workspaceId:'task',provider:'pi/existing-model'};
  for(const hook of loaded.extensions[0].handlers.get('tool_call'))result=await hook({toolName:'paseo_create_agent',input},{cwd:root});
  assert.equal(Boolean(result?.block),expected,`missing or mismatched managed mainRepoRoot must reject: ${JSON.stringify(patch)}: ${result?.reason}`);cases++;
 }
 console.log(`PASS: ${cases} native managed-provenance cases; omitted/null/type/wrong root reject, actual canonical root permits launch.`);
}finally{if(previous===undefined)delete process.env.PASEO_HOME;else process.env.PASEO_HOME=previous;rmSync(temp,{recursive:true,force:true});}
