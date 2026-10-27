// A task-owned LayerFS bridge for Pi-Bolt. The Mac worktree is immutable until
// an explicit, independently audited Git bundle handoff. Never retry a call
// after an uncertain outcome, or fall back to host filesystem operations.
import { readFile, writeFile, mkdir, realpath, rm, access } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { join, resolve, relative, isAbsolute, dirname } from 'node:path';

const root = process.env.MEGAI_LAYERFS_ROOT || '/Users/bro/.local/share/layerfs-task-73fddf83';
const source = join(root, 'source');
const bundle = join(root, 'build-resources/source-2dae3b5e922d/artifacts/build-linux-421c217a87624dd3b600a767a76bd251');
const image = 'sha256:c966e68bc796a95855bb565f0dc7366b89f2ce73c265dbc00662dfe49b302f89';
const prefix = 'layerfs73fddf83-';
const quote = s => `'${String(s).replaceAll("'", "'\\''")}'`;
const fatal = message => { throw new Error(message); };
const validId = id => /^[a-f0-9]{32}$/.test(id);
function run(exe, args, cwd) {
  return new Promise((resolve, reject) => {
    const p = spawn(exe, args, { cwd, stdio: ['ignore','pipe','pipe'], env: { ...process.env, GIT_TERMINAL_PROMPT: '0' } });
    let stdout='', stderr='';
    p.stdout.on('data', b => stdout += b); p.stderr.on('data', b => stderr += b);
    p.on('error', reject); p.on('close', code => code === 0 ? resolve(stdout.trim()) : reject(Error(`${exe} exit ${code}: ${stderr.trim()}`)));
  });
}
const git = (cwd, ...args) => run('git', args, cwd);
const stateDir = id => join(root,'tasks',id);
const stateFile = id => join(stateDir(id),'state.json');
const copyState = s => ({schema:1,taskId:s.taskId,worktree:s.worktree,branch:s.branch,base:s.base,project:s.project,sandbox:s.sandbox,workspace:s.workspace,phase:s.phase,owner:s.owner??null});
async function save(s) { await writeFile(stateFile(s.taskId),JSON.stringify(copyState(s))+'\n',{mode:0o600}); }
async function load(id) {
  if (!validId(id)) fatal('Invalid Pellet UUID');
  const s=JSON.parse(await readFile(stateFile(id),'utf8'));
  if (s.schema!==1 || s.taskId!==id || !s.workspace || s.phase!=='ready') fatal('Task state incomplete; reconcile, never retry automatically');
  return s;
}
async function runtime() {
  const {LayerFSRuntime}=await import(`${source}/api/runtime/src/index.js`);
  if(await git(source,'rev-parse','HEAD')!=='9f97a7ec95b662e9cb288704afa165feff132cfa' ||
     await git(source,'status','--porcelain=v1','--untracked-files=all')) fatal('Pinned LayerFS source changed; no default execution');
  return LayerFSRuntime.open({home:join(root,'home'),bundle,image,containerPrefix:prefix,sweep:false});
}
async function agent(rt,record) {
  const [{LayerFS},{deploymentEnv,withEnv}]=await Promise.all([
    import(`${source}/api/agent/sdk/src/index.js`),import(`${source}/api/runtime/src/clients.js`)]);
  return withEnv(deploymentEnv(rt.settings,rt.platform,record),()=>LayerFS.open(record.name));
}
async function project(rt,s) {
  const record=(await rt.project.list()).find(p=>p.name===s.project);
  if (!record) fatal('LayerFS project missing; no host fallback');
  return agent(rt,record);
}
async function provision({taskId,worktree}) {
  if (!validId(taskId)) fatal('Invalid Pellet UUID');
  if (!isAbsolute(worktree) || await realpath(worktree)!==worktree) fatal('Worktree must be a canonical absolute path');
  if (await git(worktree,'rev-parse','--show-toplevel')!==worktree) fatal('Not a Git worktree root');
  const branch=await git(worktree,'symbolic-ref','--short','HEAD');
  if (branch!==`task/factory-${taskId}` && branch!==`task/layerfs-${taskId}` &&
      branch!==`task/layerfs-${taskId.slice(0,8)}`) fatal('Branch does not bind this Pellet task');
  const trees=await git(worktree,'worktree','list','--porcelain');
  const owned=trees.split('\n\n').find(block=>block.split('\n')[0]===`worktree ${worktree}`);
  if (!owned || !owned.split('\n').includes(`branch refs/heads/${branch}`)) fatal('Cannot prove task worktree ownership');
  if (await git(worktree,'status','--porcelain=v1','--untracked-files=all')) fatal('Dirty task worktree: refusing snapshot');
  const hostRemote=await git(worktree,'remote','get-url','origin');
  const pushRemote=await git(worktree,'remote','get-url','--push','origin');
  if (hostRemote!=='https://github.com/ExcuseMeBro/MEGAI.git' || pushRemote!==hostRemote) fatal('Unverified MEGAI remote');
  const base=await git(worktree,'rev-parse','HEAD');
  await git(worktree,'merge-base','--is-ancestor','dev',base);
  const dir=stateDir(taskId);
  await mkdir(join(root,'tasks'),{recursive:true,mode:0o700});
  await mkdir(dir,{recursive:false,mode:0o700}); // exclusive claim; existing receipt blocks implicit retry
  const s={schema:1,taskId,worktree,branch,base,project:`task${taskId}`,sandbox:null,workspace:null,phase:'preparing'};
  await save(s);
  const snapshot=join(dir,'snapshot');
  await run('git',['clone','--quiet','--no-local','--no-hardlinks','--single-branch','--branch',branch,worktree,snapshot],root);
  await git(snapshot,'remote','remove','origin');
  await git(snapshot,'config','core.hooksPath','/dev/null');
  if (await git(snapshot,'rev-parse','HEAD')!==base) fatal('Snapshot HEAD changed');
  const rt=await runtime();
  let layer;
  try {
    const worker=await rt.worker.start();
    if (!worker.worker?.answering) fatal('LayerFS worker unavailable');
    const job=await rt.project.start_init(s.project,snapshot,{timeout:300000});
    // Job API is asynchronous: bounded init observation, never retry an unknown import.
    const deadline=Date.now()+315000;
    let result;
    while (Date.now()<deadline) {
      result=await rt.project.get_init(job.id);
      if (result?.ended) break;
      await new Promise(r=>setTimeout(r,500));
    }
    if (!result?.ended || result.error) fatal(`LayerFS init unresolved: ${JSON.stringify({step:result?.step,error:result?.error})}`);
    s.phase='imported'; await save(s);
    layer=await agent(rt,result.project);
    const branchName='task';
    await layer.branch.fork(branchName);
    s.sandbox=(await layer.sandbox.create()).sandbox;
    s.workspace=await layer.workspace.mount(s.sandbox,branchName);
    const check=await layer.workspace.exec(s.workspace,`test "$(git rev-parse HEAD)" = ${quote(base)} && test -z "$(git status --porcelain)"`,'verify isolated Git source');
    if (check.exitCode!==0) fatal('Imported source does not match clean task HEAD');
    s.phase='ready'; await save(s);
    return {taskId,project:s.project,workspace:s.workspace.path,base};
  } finally { await layer?.close(); await rt.close(); }
}
function inside(s,p) {
  const full=resolve(s.worktree,p);
  const rel=relative(s.worktree,full);
  if (rel==='..' || rel.startsWith('../') || isAbsolute(rel) || full===s.worktree && p==='..') fatal('Path outside task worktree');
  return join(s.workspace.path,rel);
}
async function attach({taskId,worktree}) {
  const sessionLock=join(stateDir(taskId),'session.lock');
  await mkdir(sessionLock,{mode:0o700}); // one task session, never steal an uncertain owner
  let rt,layer,started=false;
  try {
    const s=await load(taskId);
    if(s.owner) fatal('Task already owned by a Pi session; do not attach or stop it');
    try { await access(join(stateDir(taskId),'operation.lock')); fatal('Task operation in progress'); }
    catch(e) { if(e.code!=='ENOENT') throw e; }
    if(s.worktree!==worktree || await realpath(worktree)!==worktree ||
       await git(worktree,'symbolic-ref','--short','HEAD')!==s.branch ||
       await git(worktree,'rev-parse','HEAD')!==s.base ||
       await git(worktree,'status','--porcelain=v1','--untracked-files=all')) fatal('Task Git worktree drifted or is dirty');
    rt=await runtime();
    const status=await rt.status();
    if(status.missing?.length||status.worker?.state!=='running') fatal('LayerFS worker unavailable');
    layer=await project(rt,s);
    started=true;
    const checked=await layer.workspace.exec(s.workspace,`test "$(git symbolic-ref --short HEAD)" = ${quote(s.branch)} && git merge-base --is-ancestor ${quote(s.base)} HEAD`,'verify workspace attachment');
    if(checked.exitCode!==0) fatal('Workspace branch changed or diverged from task base');
    s.owner=randomUUID(); await save(s);
    return {taskId,owner:s.owner,workspace:s.workspace.path,project:s.project,base:s.base};
  } catch(e) { if(!started) await rm(sessionLock,{recursive:true}); throw e; }
  finally { await layer?.close(); await rt?.close(); }
}
async function openTask(data) {
  if(!validId(data.taskId)) fatal('Invalid Pellet UUID');
  try { await access(stateFile(data.taskId)); }
  catch(e) { if(e.code!=='ENOENT') throw e; await provision(data); }
  return attach(data);
}
async function release({taskId,owner}) {
  const s=await load(taskId);
  if(!owner||s.owner!==owner) fatal('Task session ownership changed');
  try { await access(join(stateDir(taskId),'operation.lock')); fatal('Active or uncertain operation; retain owner'); }
  catch(e) { if(e.code!=='ENOENT') throw e; }
  const rt=await runtime(); let layer;
  try {
    layer=await project(rt,s);
    const checkpoint=await layer.workspace.commit(s.workspace,'Pi session checkpoint');
    s.owner=null; await save(s);
    await rm(join(stateDir(taskId),'session.lock'),{recursive:true});
    return {checkpoint:checkpoint.kind,retained:true};
  } finally { await layer?.close(); await rt.close(); }
}
async function exportBundle({taskId}) {
  const s=await load(taskId);
  if(s.owner) fatal('A Pi session still owns this task');
  for(const name of ['session.lock','operation.lock']) {
    try { await access(join(stateDir(taskId),name)); fatal(`Task ${name} is present; reconcile before export`); }
    catch(e) { if(e.code!=='ENOENT') throw e; }
  }
  if(await git(s.worktree,'rev-parse','HEAD')!==s.base ||
     await git(s.worktree,'status','--porcelain=v1','--untracked-files=all')) fatal('Host task worktree has changed; refusing bundle');
  const lock=join(stateDir(taskId),'operation.lock'); await mkdir(lock,{mode:0o700});
  let rt,layer,started=false,finished=false;
  try {
    rt=await runtime(); layer=await project(rt,s);
    const check=await layer.workspace.exec(s.workspace,'git status --porcelain=v1 --untracked-files=all && git rev-parse HEAD','audit workspace Git state');
    if(check.exitCode!==0) fatal('Workspace Git status failed');
    const lines=check.stdout.trim().split('\n');
    if(lines.length!==1 || !/^[a-f0-9]{40}$/.test(lines[0])) fatal('Workspace has uncommitted or untracked files; commit or remove deliberately');
    const tip=lines[0];
    const ancestor=await layer.workspace.exec(s.workspace,`git merge-base --is-ancestor ${quote(s.base)} ${quote(tip)}`,'verify task commit ancestry');
    if(ancestor.exitCode!==0) fatal('Workspace task branch diverged from pinned base');
    if(tip===s.base) fatal('No new task commits to export');
    const checkpoint=await layer.workspace.commit(s.workspace,'Task Git bundle export checkpoint');
    if(!['Committed','UpToDate'].includes(checkpoint.kind)) fatal(`LayerFS checkpoint outcome ${checkpoint.kind} requires reconciliation`);
    const filename=join(stateDir(taskId),`task-${tip}.bundle`);
    const sink=createWriteStream(filename,{flags:'wx',mode:0o600});
    const command=`git bundle create /tmp/task-${taskId}.bundle HEAD ^${quote(s.base)} && cat /tmp/task-${taskId}.bundle`;
    s.phase='exporting'; await save(s); started=true;
    let result;
    try { result=await layer.workspace.exec(s.workspace,command,'export exact task Git bundle',{stdout:sink}); }
    finally { await new Promise((done,fail)=>sink.end(error=>error?fail(error):done())); }
    if(result.exitCode!==0) fatal(`Bundle export exited ${result.exitCode}: ${result.stderr}`);
    await git(s.worktree,'bundle','verify',filename);
    const head=await git(s.worktree,'bundle','list-heads',filename);
    if(!head.startsWith(`${tip} HEAD`)) fatal('Bundle ref does not match task tip');
    s.phase='ready'; await save(s); finished=true;
    return {taskId,base:s.base,tip,bundle:filename,checkpoint:checkpoint.kind,note:'Bundle verified, NOT merged or delivered; audit the complete commit range before fetching into the task worktree.'};
  } finally {
    await layer?.close(); await rt?.close();
    if(!started || finished) await rm(lock,{recursive:true});
  }
}
async function operate({taskId,owner,action,path,cwd,content,command,timeout}) {
  const s=await load(taskId);
  if(s.owner && s.owner!==owner) fatal('Task is owned by another Pi session');
  if(!s.owner) {
    try { await access(join(stateDir(taskId),'session.lock')); fatal('Task session is attaching; refusing direct operation'); }
    catch(e) { if(e.code!=='ENOENT') throw e; }
  }
  const lock=join(stateDir(taskId),'operation.lock');
  await mkdir(lock,{mode:0o700}); // fail closed for concurrent calls, don't replay uncertain writes
  let rt, layer, started=false, finished=false;
  try {
    rt=await runtime();
    const status=await rt.status();
    if (status.missing?.length || status.worker?.state!=='running') fatal('LayerFS worker unavailable');
    layer=await project(rt,s);
    const ws=s.workspace;
    let shell;
    if (action==='bash') {
      const limit=timeout??120;
      if (typeof command!=='string' || !Number.isSafeInteger(limit) || limit<1 || limit>86400) fatal('Invalid bounded shell request');
      shell=`cd ${quote(inside(s,cwd||s.worktree))} && timeout -k 5s ${limit}s sh -lc ${quote(command)}`;
    } else if (action==='read') {
      shell=`base64 -w 0 -- ${quote(inside(s,path))}`;
    } else if (action==='access') {
      shell=`test -r ${quote(inside(s,path))}`;
    } else if (action==='mkdir') {
      shell=`mkdir -p -- ${quote(inside(s,path))}`;
    } else if (action==='write') {
      if (typeof content!=='string' || content.length>700000 || !/^[A-Za-z0-9+/=]*$/.test(content)) fatal('Invalid or oversized base64 write');
      const dest=inside(s,path);
      shell=`mkdir -p -- ${quote(dirname(dest))} && printf %s ${quote(content)} | base64 -d > ${quote(dest)}`;
    } else fatal('Unsupported operation');
    s.phase='executing'; await save(s); started=true;
    const out=await layer.workspace.exec(ws,shell,`Pi ${action}`);
    s.phase='ready'; await save(s); finished=true;
    if(action!=='bash' && out.exitCode!==0) fatal(`Workspace ${action} failed (exit ${out.exitCode}): ${out.stderr}`);
    return {exitCode:out.exitCode,stdout:out.stdout,stderr:out.stderr};
  } finally {
    await layer?.close(); await rt?.close();
    if (!started || finished) await rm(lock,{recursive:true});
    // An unknown outcome keeps both the receipt phase and lock for manual reconciliation.
  }
}
async function main() {
  const data=JSON.parse(await readFile('/dev/stdin','utf8'));
  const result=data.action==='provision' ? await provision(data) :
    data.action==='open' ? await openTask(data) :
    data.action==='release' ? await release(data) :
    data.action==='export' ? await exportBundle(data) : await operate(data);
  process.stdout.write(JSON.stringify({ok:true,result})+'\n');
}
main().catch(e=>{process.stdout.write(JSON.stringify({ok:false,error:e.message})+'\n');process.exitCode=1;});
