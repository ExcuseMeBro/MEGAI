import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
const client=resolve(import.meta.dirname,'../pi-defaults/extensions/megai-layerfs/client.mjs');
const id='73fddf8386dce382fe586e03bda95030';
function call(input){
  const p=spawnSync(process.execPath,[client],{input:JSON.stringify(input),encoding:'utf8',timeout:30000});
  assert.equal(p.signal,null,`helper timed out: ${p.stderr}`);
  return {status:p.status,...JSON.parse(p.stdout)};
}
test('invalid task identity refuses operations without creating a project',()=>{
  const result=call({action:'provision',taskId:'../escape',worktree:'/tmp'});
  assert.equal(result.status,1);
  assert.match(result.error,/Invalid Pellet UUID/);
});
test('absent task receipt fails closed on read, write and export',()=>{
  for(const action of ['read','write','export']){
    const result=call({action,taskId:'0'.repeat(32),path:'/tmp/file',content:'dGVzdA=='});
    assert.equal(result.status,1);
    assert.equal(result.ok,false);
  }
});
const live=process.env.MEGAI_LAYERFS_TEST_LIVE==='1';
test('live Pi task bridge: exclusive attach, routed I/O and host escape denial', {skip:!live},()=>{
  const worktree='/Users/bro/.local/share/layerfs-task-73fddf83/factory-probe';
  const opened=call({action:'open',taskId:id,worktree});
  assert.equal(opened.status,0,opened.error);
  const owner=opened.result.owner;
  try{
    assert.match(owner,/^[0-9a-f-]{36}$/);
    const second=call({action:'open',taskId:id,worktree});
    assert.equal(second.status,1,'concurrent Pi attachment must fail');
    const p=worktree+'/layerfs-route-probe.txt';
    const read=call({action:'read',taskId:id,owner,path:p});
    assert.equal(Buffer.from(read.result.stdout,'base64').toString(),'isolated proof\n');
    assert.equal(existsSync(p),false,'host worktree must remain untouched');
    const outside=call({action:'read',taskId:id,owner,path:'/etc/passwd'});
    assert.equal(outside.status,1);
    assert.match(outside.error,/outside task worktree/);
    const withoutOwner=call({action:'read',taskId:id,path:p});
    assert.equal(withoutOwner.status,1);
    const shell=call({action:'bash',taskId:id,owner,cwd:worktree,command:'pwd; git status --porcelain',timeout:10});
    assert.equal(shell.result.exitCode,0);
    assert.match(shell.result.stdout,/^\/workspaces\/\d+\n/);
    assert.equal(existsSync(p),false);
  } finally {
    const released=call({action:'release',taskId:id,owner});
    assert.equal(released.status,0,released.error);
    assert.equal(released.result.retained,true);
  }
});
