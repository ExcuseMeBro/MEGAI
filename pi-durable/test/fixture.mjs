import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { Type } from '@earendil-works/pi-ai';
import { createModels } from '@earendil-works/pi-ai/models';
import { fauxAssistantMessage, fauxProvider, fauxToolCall } from '@earendil-works/pi-ai/providers/faux';
import { defineTool } from '@earendil-works/pi-durable';

export async function create(_config, taskDir) {
  const behavior = JSON.parse(readFileSync(join(taskDir, 'fixture.json')));
  if (behavior.startupCrash) {
    appendFileSync(join(taskDir, 'startups'), 'start\n');
    process.kill(process.pid, 'SIGKILL');
  }
  const faux = fauxProvider({ api: 'test-faux', models: [{ id: 'faux-1', reasoning: true }] });
  const models = createModels(); models.setProvider(faux.provider);
  const response = transcript => {
    appendFileSync(join(taskDir, 'model-calls'), 'call\n');
    if (behavior.providerError) return fauxAssistantMessage('', { stopReason: 'error', errorMessage: 'HTTP 402 Insufficient Balance' });
    const messages = transcript.messages;
    if (!behavior.tool || messages.some(message => message.role === 'toolResult')) return fauxAssistantMessage('FIXTURE_DONE');
    return fauxAssistantMessage(fauxToolCall(behavior.tool, { path: 'fixture.txt' }, { id: 'fixture-call' }), { stopReason: 'toolUse' });
  };
  faux.setResponses(Array.from({ length: 20 }, () => response));
  const tool = name => defineTool({ name, description: 'Disposable crash-test tool', parameters: Type.Object({ path: Type.String() }),
    replay: name === 'read' ? 'safe' : 'unsafe',
    execute: async (_args, _api, ctx) => {
      appendFileSync(join(taskDir, `${name}-effects`), 'effect\n');
      writeFileSync(join(taskDir, 'tool-started'), String(process.pid));
      await new Promise((resolve, reject) => {
        const timer = setInterval(() => { if (existsSync(join(taskDir, 'gate'))) { clearInterval(timer); resolve(); } }, 10);
        ctx.abortSignal?.addEventListener('abort', () => { clearInterval(timer); reject(new Error('Test tool stopped')); }, { once: true });
      });
      return { content: [{ type: 'text', text: `${name} complete` }] };
    },
  });
  return { models, tools: [tool('read'), tool('write')] };
}
