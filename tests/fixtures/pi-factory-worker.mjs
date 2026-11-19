// RPC peer for the native Pi SDK integration tests. No live providers or board.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { basename, dirname } from 'node:path';
import { createInterface } from 'node:readline';

assert.deepEqual(process.argv.slice(2, 9), ['--mode', 'rpc', '--no-session', '--no-approve', '--provider', process.argv[7], '--model']);
const [, provider, , model, , thinking] = process.argv.slice(6);
assert.equal(thinking, 'low');
assert.equal(model, 'fixture');
assert.equal(process.env.MEGAI_FACTORY_PREP_WORKER, '1');
assert.equal(process.env.GIT_ALLOW_PROTOCOL, '');
const id = Number(basename(process.cwd()));
assert.equal(basename(dirname(process.cwd())), 'factory-fixture');
const send = event => process.stdout.write(`${JSON.stringify(event)}\n`);
async function ask(phase) {
  const response = await fetch(`${process.env.PI_FACTORY_TEST_URL}/worker?id=${id}&pid=${process.pid}&phase=${phase}`);
  assert.ok(response.ok);
  return response.text();
}
for await (const line of createInterface({ input: process.stdin })) {
  const command = JSON.parse(line);
  if (command.type === 'get_state') {
    const mode = await ask('state');
    send({ type: 'response', id: command.id, success: true,
      data: { model: { provider, id: mode === 'mismatch' ? 'wrong' : model }, thinkingLevel: thinking } });
  } else {
    assert.equal(command.type, 'prompt');
    assert.match(command.message, new RegExp(`only Brokan factory-fixture#${id} on`));
    assert.match(command.message, /Do not change or switch branches, create a worktree, merge to dev or main, push/);
    send({ type: 'response', id: command.id, success: true, data: { disposition: 'started' } });
    const result = await ask('prompt');
    if (result === 'interactive') {
      send({ type: 'extension_ui_request', id: 'confirm-required', method: 'confirm' });
      continue;
    }
    if (result === 'ready') {
      writeFileSync(`task-${id}.txt`, `Candidate for ${id}\n`);
      execFileSync('git', ['add', `task-${id}.txt`]);
      execFileSync('git', ['commit', '-qm', `Prepare ${id}`]);
    }
    send({ type: 'message_end', message: { role: 'assistant', stopReason: 'stop', content: [{ type: 'text', text: result === 'pause' ? 'FACTORY_PAUSE' : 'FACTORY_READY' }] } });
    send({ type: 'agent_settled', aborted: false });
  }
}
