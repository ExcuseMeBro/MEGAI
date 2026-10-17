import { web } from '@e2e-dev/web';
import { chatgpt } from 'e2e/oauth/chatgpt';
import type { E2EConfig } from 'e2e';
import { appendFileSync } from 'node:fs';

const native = chatgpt('gpt-6.1-sol');
const audit = (result: Awaited<ReturnType<typeof native.doGenerate>>) => {
  const body = result.request?.body;
  const request = typeof body === 'string' ? JSON.parse(body) : body ?? {};
  const receipt = { model: request.model, reasoning: request.reasoning, usage: result.usage };
  appendFileSync(process.env.BENCH_REQUEST_RECEIPT!, JSON.stringify(receipt) + '\n', { mode: 0o600 });
  if (request.model !== 'gpt-6.1-sol' || request.reasoning?.effort !== 'high') throw new Error('Native e2e request did not select GPT-6.1-Sol high');
  return result;
};
const model = {
  ...native,
  doGenerate: async (options: Parameters<typeof native.doGenerate>[0]) => audit(await native.doGenerate(options)),
};

export default {
  projectId: 'megai-pi-e2e-benchmark',
  targets: [{
    name: 'web',
    engine: web({ viewport: { width: 1280, height: 720 } }),
    app: { url: process.env.BENCH_APP_URL!, identity: 'megai-local-bench-fixture' },
  }],
  tests: ['tests/flow.e2e.ts'],
  agents: { default: {
    model,
    providerOptions: { openai: { reasoningEffort: 'high', forceReasoning: true } },
    maxSteps: 15,
    maxModelCalls: 12,
  } },
  cache: { mode: 'read-write', dir: process.env.BENCH_CACHE_DIR! },
  timeout: 240000,
  retries: 0,
  workers: 1,
  trace: 'off',
  video: 'off',
  reporters: ['list'],
} satisfies E2EConfig;
