function count(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error('Missing or invalid token counter');
  return value;
}

export function piUsage(events) {
  const result = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0, calls: 0, models: [], errors: [] };
  for (const event of events) {
    if (event.type !== 'message_end' || event.message?.role !== 'assistant') continue;
    const message = event.message;
    const usage = message.usage;
    if (!usage) throw new Error('Missing Pi token accounting');
    if (count(usage.totalTokens) !== count(usage.input) + count(usage.output) + count(usage.cacheRead) + count(usage.cacheWrite)) throw new Error('Inconsistent Pi token total');
    result.calls++;
    result.input += usage.input;
    result.output += usage.output;
    result.cacheRead += usage.cacheRead;
    result.cacheWrite += usage.cacheWrite;
    result.total += usage.totalTokens;
    result.models.push(message.provider + '/' + message.model);
    if (['error', 'aborted'].includes(message.stopReason)) result.errors.push(message.errorMessage ?? message.stopReason);
  }
  result.models = [...new Set(result.models)];
  if (result.models.some((m) => m !== 'openai-codex/gpt-6.1-sol')) throw new Error('Pi model mismatch');
  return result;
}

export function e2eUsage(report) {
  const result = { input: 0, output: 0, cacheRead: 0, total: 0, calls: 0, models: [], accounting: [], cache: [], statuses: [] };
  for (const test of report.run.results) {
    result.statuses.push(test.status);
    for (const attempt of test.attempts) {
      for (const step of attempt.steps) {
        if (step.cache) result.cache.push(step.cache);
        if (!step.model) continue;
        const model = step.model;
        result.input += count(model.inputTokens);
        result.output += count(model.outputTokens);
        result.cacheRead += model.calls === 0 ? 0 : count(model.cacheReadTokens);
        result.calls += count(model.calls);
        result.models.push(model.provider + '/' + model.model);
        result.accounting.push(model.tokenAccounting);
      }
    }
  }
  result.total = result.input + result.output;
  result.models = [...new Set(result.models)];
  result.accounting = [...new Set(result.accounting)];
  if (result.accounting.some((x) => x !== 'provider')) throw new Error('Non-authoritative e2e usage');
  if (result.models.some((x) => x !== 'chatgpt.responses/gpt-6.1-sol')) throw new Error('e2e model mismatch');
  return result;
}
