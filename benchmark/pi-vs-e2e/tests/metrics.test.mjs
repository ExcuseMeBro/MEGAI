import test from 'node:test';
import assert from 'node:assert/strict';
import { piUsage, e2eUsage } from '../metrics.mjs';
import { startFixture, acceptance } from '../fixture.mjs';

const message = {
  role: 'assistant', provider: 'openai-codex', model: 'gpt-6.1-sol', stopReason: 'stop',
  usage: { input: 100, output: 20, cacheRead: 80, cacheWrite: 0, totalTokens: 200 },
};
const step = {
  model: { provider: 'chatgpt.responses', model: 'gpt-6.1-sol', calls: 2, inputTokens: 100, outputTokens: 20, cacheReadTokens: 80, tokenAccounting: 'provider' },
  events: [{ kind: 'model', inputTokens: 100, outputTokens: 20 }],
};
const report = (steps) => ({ run: { results: [{ status: 'passed', attempts: [{ steps }] }] } });

test('Pi counts only completed assistant messages, never stream snapshots or turn copies', () => {
  const usage = piUsage([
    { type: 'message_update', usage: message.usage },
    { type: 'message_end', message },
    { type: 'turn_end', message },
    { type: 'message_end', message: { role: 'toolResult', usage: message.usage } },
  ]);
  assert.equal(usage.calls, 1);
  assert.equal(usage.total, 200);
  assert.equal(usage.cacheRead, 80);
});
test('e2e cache reads are included in input, not added twice, and model events are not totals', () => {
  const usage = e2eUsage(report([step]));
  assert.equal(usage.total, 120);
  assert.equal(usage.cacheRead, 80);
  assert.equal(usage.calls, 2);
  assert.equal(piUsage([{ type: 'message_end', message }]).total + usage.total, 320);
});
test('Pure e2e replay has zero nested model calls but retains replay evidence', () => {
  const usage = e2eUsage(report([{ cache: { mode: 'self-finalized', replayedActions: 7 }, events: [] }]));
  assert.equal(usage.total, 0);
  assert.equal(usage.calls, 0);
  assert.equal(usage.cache[0].replayedActions, 7);
});
test('Reject missing accounting, bad counters, wrong models and upper-bound estimates', () => {
  assert.throws(() => piUsage([{ type: 'message_end', message: { ...message, usage: undefined } }]));
  assert.throws(() => piUsage([{ type: 'message_end', message: { ...message, model: 'other' } }]));
  assert.throws(() => piUsage([{ type: 'message_end', message: { ...message, usage: { ...message.usage, totalTokens: 999 } } }]));
  assert.throws(() => e2eUsage(report([{ ...step, model: { ...step.model, tokenAccounting: 'adapter-upper-bound' } }])));
  assert.throws(() => e2eUsage(report([{ ...step, model: { ...step.model, cacheReadTokens: undefined } }])));
  assert.throws(() => e2eUsage(report([{ ...step, model: { ...step.model, provider: 'wrong-provider' } }])));
});
test('Fixture requires correct login and persists exactly one project; fresh fixtures are isolated', async () => {
  const fixture = await startFixture();
  try {
    assert.equal(acceptance(fixture.state), false);
    const rejected = await fetch(fixture.url + '/login', { method: 'POST', body: new URLSearchParams({ email: 'wrong', password: 'wrong' }), redirect: 'manual' });
    assert.equal(rejected.status, 401);
    assert.equal(fixture.state.logins, 0);
    const denied = await fetch(fixture.url + '/projects/new', { redirect: 'manual' });
    assert.equal(denied.status, 303);
    const login = await fetch(fixture.url + '/login', { method: 'POST', body: new URLSearchParams({ email: 'bench@example.test', password: 'demo-password' }), redirect: 'manual' });
    assert.equal(login.status, 303);
    const cookie = login.headers.get('set-cookie').split(';')[0];
    const created = await fetch(fixture.url + '/projects', { method: 'POST', headers: { cookie }, body: new URLSearchParams({ name: 'Bench Project', description: 'Token and speed benchmark' }), redirect: 'manual' });
    assert.equal(created.status, 303);
    const detail = await fetch(fixture.url + created.headers.get('location'), { headers: { cookie } });
    assert.match(await detail.text(), /role="status">Project created/);
    assert.equal(acceptance(fixture.state), true);
    const fresh = await startFixture();
    try { assert.equal(acceptance(fresh.state), false); assert.deepEqual(fresh.state.projects, []); }
    finally { await new Promise((resolve) => fresh.server.close(resolve)); }
    fixture.state.projects.push({ name: 'duplicate' });
    assert.equal(acceptance(fixture.state), false);
  } finally { await new Promise((resolve) => fixture.server.close(resolve)); }
});
