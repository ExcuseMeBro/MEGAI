// Fail-closed Pi-Bolt task bridge. Only a verified Pellet task-owned Git
// worktree is eligible. Unbound task worktrees never silently use the Mac.
import { spawn, execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import {
  createBashTool, createEditTool, createReadTool, createWriteTool,
  type BashOperations, type ReadOperations, type WriteOperations,
} from '@earendil-works/pi-coding-agent';
const client = fileURLToPath(new URL('./client.mjs', import.meta.url));
const node = '/usr/local/bin/node';
type State = { kind: 'local' | 'blocked' | 'layerfs'; taskId?: string; owner?: string; reason?: string };

function rpc(input: Record<string, unknown>): Promise<{ stdout: string; stderr: string; exitCode: number; owner?: string }> {
  return new Promise((resolve, reject) => {
    const p=spawn(node,[client],{stdio:['pipe','pipe','pipe']});
    let out='',err='';
    p.stdout.on('data',(b:Buffer)=>out+=b.toString());
    p.stderr.on('data',(b:Buffer)=>err+=b.toString());
    p.on('error',reject);
    p.on('close',code=>{
      try {
        const reply=JSON.parse(out);
        if(code!==0 || !reply.ok) reject(new Error(`LayerFS blocked: ${reply.error ?? err}`));
        else resolve(reply.result);
      } catch(e) { reject(new Error(`LayerFS helper failed closed: ${String(e)} (${err})`)); }
    });
    p.stdin.on('error',reject);
    p.stdin.end(JSON.stringify(input));
  });
}
function taskBranch(cwd:string): State {
  let branch:string;
  try { branch=execFileSync('git',['symbolic-ref','--short','HEAD'],{cwd,encoding:'utf8',timeout:2000}).trim(); }
  catch {
    let parent=cwd;
    while(true){
      if(existsSync(join(parent,'.git'))||process.env.GIT_DIR)return {kind:'blocked',reason:'Cannot establish Git task identity; no host fallback'};
      const next=dirname(parent);
      if(next===parent)break;
      parent=next;
    }
    return {kind:'local'}; // outside a Git checkout, no task-owned worktree exists
  }
  if(branch==='dev'||branch==='main')return {kind:'local'};
  if(!branch.startsWith('task/'))return {kind:'blocked',reason:'Non-dev Git branch has no verified Pellet task binding'};
  const automatic=/^task\/(?:factory|layerfs)-([a-f0-9]{32})$/.exec(branch);
  const explicit=process.env.MEGAI_PELLET_TASK_ID;
  const manual=/^task\/layerfs-([a-f0-9]{8})$/.exec(branch);
  const id=automatic?.[1] ?? (manual && explicit?.startsWith(manual[1]) && /^[a-f0-9]{32}$/.test(explicit) ? explicit : undefined);
  return id ? {kind:'blocked',taskId:id,reason:'LayerFS task is provisioning'} : {kind:'blocked',reason:'Task branch has no verified Pellet UUID binding'};
}
function remoteOps(taskId:string, owner:string, cwd:string) {
  const call=(action:string, path:string, content?:string)=>rpc({taskId,owner,action,path,content});
  const read:ReadOperations={
    readFile:async path=>Buffer.from((await call('read',path)).stdout,'base64'),
    access:async path=>{await call('access',path);},
    detectImageMimeType:async path=>{
      const bytes=Buffer.from((await call('read',path)).stdout,'base64');
      if(bytes.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))return 'image/png';
      if(bytes.subarray(0,3).equals(Buffer.from([255,216,255])))return 'image/jpeg';
      if(bytes.subarray(0,4).toString()==='GIF8')return 'image/gif';
      if(bytes.subarray(0,4).toString()==='RIFF' && bytes.subarray(8,12).toString()==='WEBP')return 'image/webp';
      return null;
    },
  };
  const write:WriteOperations={
    writeFile:async(path,content)=>{await call('write',path,Buffer.from(content).toString('base64'));},
    mkdir:async path=>{await call('mkdir',path);},
  };
  const bash:BashOperations={
    exec:async(command,dir,{onData,signal,timeout})=>{
      if(signal?.aborted)throw new Error('LayerFS command aborted before start');
      const result=await rpc({taskId,owner,action:'bash',cwd:dir||cwd,command,timeout});
      if(result.stdout)onData(Buffer.from(result.stdout));
      if(result.stderr)onData(Buffer.from(result.stderr));
      if(signal?.aborted)throw new Error('LayerFS command completed after abort; inspect receipt');
      return {exitCode:result.exitCode};
    },
  };
  return {read,write,bash};
}
export default function layerfsTask(pi:ExtensionAPI) {
  const cwd=process.cwd();
  const local={read:createReadTool(cwd),write:createWriteTool(cwd),edit:createEditTool(cwd),bash:createBashTool(cwd)};
  let state:State=taskBranch(cwd);
  function requireTask():{id:string;owner:string} {
    if(state.kind!=='layerfs'||!state.taskId||!state.owner)throw new Error(state.reason||'LayerFS task is unavailable');
    return {id:state.taskId,owner:state.owner};
  }
  pi.on('session_start',async(_event,ctx)=>{
    state=taskBranch(ctx.cwd);
    if(!state.taskId){
      if(state.kind==='blocked')ctx.ui.setStatus('megai-layerfs','LayerFS blocked: no task binding');
      return;
    }
    try {
      const opened=await rpc({action:'open',taskId:state.taskId,worktree:ctx.cwd});
      if(!opened.owner)throw new Error('LayerFS owner missing');
      state={kind:'layerfs',taskId:state.taskId,owner:opened.owner};
      ctx.ui.setStatus('megai-layerfs','LayerFS task workspace active');
    } catch(e) {
      state={kind:'blocked',reason:String(e)};
      ctx.ui.setStatus('megai-layerfs','LayerFS blocked: no host fallback');
    }
  });
  pi.on('session_shutdown',async()=>{
    if(state.kind!=='layerfs'||!state.taskId||!state.owner)return;
    try { await rpc({action:'release',taskId:state.taskId,owner:state.owner}); }
    catch { /* retain receipt/worker/Workspace and fail closed on next attach */ }
  });
  pi.on('tool_call',event=>{
    if(state.kind==='local')return;
    const tool=event.toolName;
    if(['read','write','edit','bash'].includes(tool))return;
    if(tool.startsWith('mcp__pellet__'))return; // tracking only; source tools remain blocked
    return {block:true,reason:`LayerFS task: tool ${tool} cannot be proven workspace-scoped. Use the routed core tools or reconcile the task; no host fallback.`};
  });
  pi.registerTool({...local.read,async execute(id,params,signal,onUpdate,ctx){
    if(state.kind==='local')return local.read.execute(id,params,signal,onUpdate,ctx);
    const {id:taskId,owner}=requireTask();
    const {read}=remoteOps(taskId,owner,cwd);
    return createReadTool(cwd,{operations:read}).execute(id,params,signal,onUpdate);
  }});
  pi.registerTool({...local.write,async execute(id,params,signal,onUpdate,ctx){
    if(state.kind==='local')return local.write.execute(id,params,signal,onUpdate,ctx);
    const {id:taskId,owner}=requireTask();
    const {write}=remoteOps(taskId,owner,cwd);
    return createWriteTool(cwd,{operations:write}).execute(id,params,signal,onUpdate);
  }});
  pi.registerTool({...local.edit,async execute(id,params,signal,onUpdate,ctx){
    if(state.kind==='local')return local.edit.execute(id,params,signal,onUpdate,ctx);
    const {id:taskId,owner}=requireTask();
    const {read,write}=remoteOps(taskId,owner,cwd);
    return createEditTool(cwd,{operations:{readFile:read.readFile,access:read.access,writeFile:write.writeFile}}).execute(id,params,signal,onUpdate);
  }});
  pi.registerTool({...local.bash,async execute(id,params,signal,onUpdate,ctx){
    if(state.kind==='local')return local.bash.execute(id,params,signal,onUpdate,ctx);
    const {id:taskId,owner}=requireTask();
    const {bash}=remoteOps(taskId,owner,cwd);
    return createBashTool(cwd,{operations:bash}).execute(id,params,signal,onUpdate);
  }});
  pi.on('user_bash',()=>{
    if(state.kind==='local')return;
    const {id,owner}=requireTask();
    return {operations:remoteOps(id,owner,cwd).bash};
  });
  pi.on('before_agent_start',event=>{
    if(state.kind==='local')return;
    return {systemPrompt:`${event.systemPrompt}\n\nLayerFS task isolation: ${state.kind==='layerfs'?'active workspace; core file and shell tools route into Linux LayerFS.':'BLOCKED, do not edit project source; report the blocker.'} Other tools are blocked to prevent host filesystem escape. Git commits inside the workspace are not delivered to the host worktree until a separately verified Git bundle handoff. After a failed/timeout shell call, inspect state before any repeat; never blindly replay uncertain effects. Never claim dev delivery from a workspace commit.`};
  });
}
