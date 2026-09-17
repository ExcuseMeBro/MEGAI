// Native Pi hook with real independent Git repos; no live Paseo registry mutation.
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync, realpathSync, symlinkSync } from 'node:fs';
import { execFileSync, spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const { DefaultResourceLoader, SettingsManager } = await import(pathToFileURL(join(process.env.PI_PACKAGE_ROOT,'dist/index.js')));
const temp=realpathSync(mkdtempSync(join(tmpdir(),'hybrid-workspace-'))), oldHome=process.env.PASEO_HOME;
try {
  const root=join(temp,'umbrella'), home=join(temp,'paseo');
  mkdirSync(join(root,'infra'),{recursive:true});mkdirSync(join(home,'projects'),{recursive:true});
  process.env.PASEO_HOME=home;
  const git=(cwd,...args)=>execFileSync('git',['-C',cwd,...args],{encoding:'utf8',stdio:'pipe'}).trim();
  const projects=[{projectId:'umbrella',rootPath:root,kind:'non_git'}];
  const rows=[{workspaceId:'local',projectId:'umbrella',cwd:root,kind:'directory',isPaseoOwnedWorktree:false,worktreeRoot:null}];
  const save=()=>{writeFileSync(join(home,'projects/projects.json'),JSON.stringify(projects));writeFileSync(join(home,'projects/workspaces.json'),JSON.stringify(rows));};
  const repos=['backend','frontend','mobile'].map(name=>{
    const repo=join(root,name),tree=join(home,'worktrees',name,'task-123');mkdirSync(repo);
    git(repo,'init','-q','-b','dev');git(repo,'config','user.name','Fixture');git(repo,'config','user.email','fixture@example.invalid');
    writeFileSync(join(repo,'source.txt'),'base\n');git(repo,'add','source.txt');git(repo,'commit','-qm','base');git(repo,'branch','main');
    return {name,repo,tree,base:git(repo,'rev-parse','dev')};
  });save();
  const loader=new DefaultResourceLoader({cwd:root,agentDir:join(temp,'agent'),settingsManager:SettingsManager.inMemory({packages:[]}),additionalExtensionPaths:[process.env.MEGAI_TEST_GUARD || resolve('pi-skill/workspace-guard/index.ts')]});
  await loader.reload();const loaded=loader.getExtensions();assert.deepEqual(loaded.errors,[]);assert.equal(loaded.extensions.length,1);let cases=0;
  const check=async(toolName,input,blocked,cwd=root)=>{
    let result;const before=structuredClone(input);
    for(const hook of loaded.extensions[0].handlers.get('tool_call'))result=await hook({toolName,input},{cwd});
    assert.equal(Boolean(result?.block),blocked,`hybrid child worktree must keep umbrella project: ${toolName} ${JSON.stringify(input)}: ${result?.reason}`);
    assert.deepEqual(input,before);cases++;
  };
  for(const r of repos){
    const input={isolation:'worktree',projectId:'umbrella',path:r.repo,baseBranch:'dev',branchName:'task/task-123',worktreeSlug:'task-123'};
    await check('paseo_create_workspace',input,false);
    await check('mcp',{tool:'paseo_create_workspace',args:JSON.stringify(input)},false);
    // Fixture models the native daemon's independent repository worktree placement.
    git(r.repo,'worktree','add','-qb','task/task-123',r.tree,'dev');
    rows.push({workspaceId:r.name,projectId:'umbrella',cwd:r.tree,kind:'worktree',isPaseoOwnedWorktree:true,worktreeRoot:r.tree,mainRepoRoot:r.repo});save();
    await check('paseo_create_agent',{workspaceId:r.name,provider:'pi/existing-model'},false);
    await check('paseo_create_agent',{workspaceId:r.name,provider:'pi/existing-model'},false,r.tree);
    const identity=spawnSync(process.execPath,[process.env.MEGAI_TEST_IDENTITY || resolve('pi-skill/workspace-guard/identity.mjs'),'--root',r.tree],{encoding:'utf8',timeout:10000});
    assert.equal(identity.status,0,identity.stderr);assert.equal(JSON.parse(identity.stdout).projectId,'umbrella');
    assert.equal(git(r.tree,'branch','--show-current'),'task/task-123');
    assert.equal(git(r.tree,'rev-parse','HEAD'),r.base);
    writeFileSync(join(r.tree,'source.txt'),r.name+' task\n');
    assert.equal(readFileSync(join(r.repo,'source.txt'),'utf8'),'base\n');
    git(r.tree,'add','source.txt');git(r.tree,'commit','-qm','task change');
  }
  const writer={workspaceId:'local',provider:'pi/existing-model',labels:{'megai.access':'write','megai.writeScope':'backend'}};
  await check('paseo_create_agent',writer,true);
  await check('paseo_create_agent',{...writer,labels:{...writer.labels,'megai.writeScope':'infra'}},false);
  await check('paseo_create_agent',{workspaceId:'local',provider:'pi/existing-model',labels:{'megai.access':'read-only'}},false);
  const input={isolation:'worktree',projectId:'umbrella',path:repos[0].repo,baseBranch:'dev',branchName:'task/task-123',worktreeSlug:'task-123'};
  for(const patch of [{path:root},{path:join(root,'infra')},{path:repos[0].tree},{path:'backend'},{projectId:'other'},{worktreeSlug:'../escape'}])await check('paseo_create_workspace',{...input,...patch},true);
  const outsider=join(temp,'outside');mkdirSync(outsider);git(outsider,'init','-q');
  await check('paseo_create_workspace',{...input,path:outsider},true);
  symlinkSync(outsider,join(root,'escape'));
  await check('paseo_create_workspace',{...input,path:join(root,'escape')},true);
  const original={...rows[1]};
  for(const patch of [{mainRepoRoot:repos[1].repo},{projectId:'other'},{isPaseoOwnedWorktree:false},{worktreeRoot:repos[1].tree},{archivedAt:'2026-01-01'}]){
    rows[1]={...original,...patch};save();await check('paseo_create_agent',{workspaceId:'backend',provider:'pi/existing-model'},true);
  }
  rows[1]=original;save();
  // Independently exercise documented Git primitives: all candidates ready, dev first;
  // no main change until the separate promotion phase, and divergence fails closed.
  for(const r of repos){assert.equal(git(r.tree,'status','--porcelain'),'');assert.equal(git(r.repo,'rev-parse','main'),r.base);}
  for(const r of repos){git(r.repo,'merge','--ff-only','task/task-123');assert.equal(git(r.repo,'rev-parse','dev'),git(r.tree,'rev-parse','HEAD'));assert.equal(git(r.repo,'rev-parse','main'),r.base);}
  for(const r of repos){git(r.repo,'switch','-q','main');git(r.repo,'merge','--ff-only','dev');assert.equal(git(r.repo,'rev-parse','main'),git(r.repo,'rev-parse','dev'));git(r.repo,'switch','-q','dev');}
  const r=repos[0],other=join(home,'worktrees/backend/other-task');git(r.repo,'worktree','add','-qb','task/other',other,r.base);
  writeFileSync(join(other,'source.txt'),'conflicting task\n');git(other,'add','source.txt');git(other,'commit','-qm','other task');
  const before=git(r.repo,'rev-parse','dev');const failed=spawnSync('git',['-C',r.repo,'merge','--ff-only','task/other'],{encoding:'utf8'});
  assert.notEqual(failed.status,0);assert.equal(git(r.repo,'rev-parse','dev'),before);assert.equal(readFileSync(join(other,'source.txt'),'utf8'),'conflicting task\n');
  assert.deepEqual(JSON.parse(readFileSync(join(home,'projects/projects.json'))),projects);
  console.log(`PASS: ${cases} native hybrid guard cases; 3 independent same-name Git worktrees/umbrella CLI; isolated files; dev-before-main primitives and divergence preservation. Approval orchestration remains parent policy, not a Git sandbox.`);
}finally{if(oldHome===undefined)delete process.env.PASEO_HOME;else process.env.PASEO_HOME=oldHome;rmSync(temp,{recursive:true,force:true});}
