import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { piUsage, e2eUsage } from './metrics.mjs';
import { acceptance } from './fixture.mjs';

const root = process.argv[2];
if (!root) throw new Error('Usage: node summarize.mjs PRIVATE_EVIDENCE_ROOT');
const output = path.dirname(fileURLToPath(import.meta.url));
const hash = (data) => crypto.createHash('sha256').update(data).digest('hex');
const parseEvents = (text) => text.split('\n').filter(Boolean).map((line) => JSON.parse(line));
const raw = (await fs.readFile(path.join(root, 'records.jsonl'), 'utf8')).split('\n').filter(Boolean).map((line) => JSON.parse(line));
const records = raw.filter((r) => r.arm !== 'e2e-preflight');
assert.equal(records.length, 12);
assert.equal(new Set(records.map((r) => r.id)).size, 12);
const receipts = [];
for (const row of records) {
  assert.equal(row.passed, true);
  assert.equal(acceptance(row.state), true);
  const directory = path.join(root, row.id);
  const pi = piUsage(parseEvents(await fs.readFile(path.join(directory, 'pi.stdout'), 'utf8')));
  assert.deepEqual(pi, row.pi);
  assert.deepEqual(pi.models, ['openai-codex/gpt-6.1-sol']);
  if (row.arm.startsWith('e2e')) {
    const report = JSON.parse(await fs.readFile(path.join(directory, 'e2e/report.json'), 'utf8'));
    assert.equal(report.run.status, 'passed');
    const nested = e2eUsage(report);
    assert.deepEqual(nested, row.e2e);
    if (row.arm === 'e2e-cold') {
      const native = (await fs.readFile(path.join(directory, 'e2e-requests.jsonl'), 'utf8')).split('\n').filter(Boolean).map((line) => JSON.parse(line));
      assert.equal(native.length, nested.calls);
      for (const request of native) {
        assert.equal(request.model, 'gpt-6.1-sol');
        assert.equal(request.reasoning.effort, 'high');
      }
      assert.equal(native.reduce((sum, r) => sum + r.usage.inputTokens.total + r.usage.outputTokens.total, 0), nested.total);
      assert.equal(native.reduce((sum, r) => sum + r.usage.inputTokens.cacheRead, 0), nested.cacheRead);
      assert.equal(nested.cache[0].reason, 'no-entry');
    } else {
      assert.equal(nested.calls, 0);
      assert.equal(nested.cache[0].mode, 'self-finalized');
      assert.equal(nested.cache[0].replayedActions, 7);
    }
  } else if (row.arm === 'pi-live') {
    assert.deepEqual(row.browserErrors, []);
    assert.equal(row.browserOperations.filter((op) => op.op === 'open').length, 1);
    assert.equal(row.browserOperations.filter((op) => op.op === 'assert' && op.name === 'Bench Project').length, 1);
  }
  assert.equal(row.totalTokens, row.pi.total + row.e2e.total);
  const files = ['pi.stdout', 'pi.stderr', 'record.json', 'prompt.txt'];
  if (row.arm.startsWith('e2e')) files.push('e2e/report.json');
  if (row.arm === 'e2e-cold') files.push('e2e-requests.jsonl');
  const hashes = {};
  for (const name of files) hashes[name] = hash(await fs.readFile(path.join(directory, name)));
  receipts.push({ id: row.id, hashes });
}
const mean = (values) => values.reduce((sum, x) => sum + x, 0) / values.length;
const median = (values) => [...values].sort((a, b) => a - b)[Math.floor(values.length / 2)];
const arms = ['pi-live', 'e2e-cold', 'e2e-warm', 'pi-saved'];
const summary = arms.map((arm) => {
  const trials = records.filter((r) => r.arm === arm);
  assert.equal(trials.length, 3);
  return {
    arm, repetitions: 3, passed: 3,
    meanSeconds: mean(trials.map((r) => r.wallSeconds)),
    medianSeconds: median(trials.map((r) => r.wallSeconds)),
    minSeconds: Math.min(...trials.map((r) => r.wallSeconds)),
    maxSeconds: Math.max(...trials.map((r) => r.wallSeconds)),
    meanTokens: mean(trials.map((r) => r.totalTokens)),
    medianTokens: median(trials.map((r) => r.totalTokens)),
    meanCachedTokens: mean(trials.map((r) => r.cacheReadTokens)),
    meanPiTokens: mean(trials.map((r) => r.pi.total)),
    meanE2eTokens: mean(trials.map((r) => r.e2e.total)),
  };
});
const sourceManifest = await fs.readFile(path.join(root, 'measured-source/SHA256SUMS'), 'utf8');
const report = {
  baseline: '7c07b9a1ce89f6e8e56e3552933b746f0111f8c5',
  model: 'gpt-6.1-sol', requestedThinking: 'high', piVersion: '1.0.0', e2eVersion: '0.16.0', webVersion: '0.11.2', playwrightVersion: '1.63.0', nodeVersion: '24.18.0',
  sourceManifest, matrixTokens: records.reduce((sum, r) => sum + r.totalTokens, 0), summary,
  records: records.map(({ id, arm, rep, wallSeconds, passed, totalTokens, cacheReadTokens, pi, e2e }) => ({ id, arm, rep, wallSeconds, passed, totalTokens, cacheReadTokens, pi, e2e })),
  receipts,
};
await fs.writeFile(path.join(output, 'results.json'), JSON.stringify(report, null, 2) + '\n');
const fmt = (value, digits = 0) => value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
const lines = [
  '# Pi vs Pi + e2e: local browser pilot', '',
  'Measured 2026-10-03 on macOS arm64. Same GPT-6.1-Sol, requested high thinking, headless Chromium, 1280×720. One frozen login -> create project -> verify flow, three trials per arm. All 12 passed independent persisted-state acceptance.', '',
  '## Results', '',
  '| Arm | Mean wall time | Median wall time | Mean total tokens | Pi tokens | e2e tokens | Cached input tokens | Pass |',
  '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |',
  ...summary.map((s) => `| ${s.arm} | ${fmt(s.meanSeconds, 2)}s | ${fmt(s.medianSeconds, 2)}s | ${fmt(s.meanTokens)} | ${fmt(s.meanPiTokens)} | ${fmt(s.meanE2eTokens)} | ${fmt(s.meanCachedTokens)} | 3/3 |`), '',
  '`Total tokens` includes prompt-cache reads, not just uncached input. e2e input already includes its cached portion; Pi reports that portion separately. The two sources are normalized without double-counting. Every completed Pi assistant message is counted once. Nested e2e totals are reconciled with each native SDK response receipt, not inferred from Pi shell output.', '',
  '## Interpretation', '',
  `- Cold e2e used ${fmt(summary[1].meanTokens / summary[0].meanTokens, 2)}× the tokens and ${fmt(summary[1].meanSeconds / summary[0].meanSeconds, 2)}× the time of live Pi + Playwright. It made eight nested model calls per trial; live Pi made five, six and five calls and batched form actions.`,
  `- Warm e2e reduced total tokens by ${fmt(100 * (1 - summary[2].meanTokens / summary[0].meanTokens), 1)}% and wall time by ${fmt(100 * (1 - summary[2].meanSeconds / summary[0].meanSeconds), 1)}% versus live Pi. All three warm runs replayed seven actions with zero nested model calls. Pi still made two calls to launch and summarize the test.`,
  '- The saved Playwright control was cheaper and faster than warm e2e. Replay is not unique to e2e; deterministic tests need no model at all when run directly in CI. Those CI-only runs were not timed in this pilot.',
  '- For this stable flow, e2e is not a first-run token/speed optimization. Its reason to adopt would be natural-language test authoring and recovery when UI changes; recovery and UI churn were not measured here.', '',
  '## Individual trials', '',
  '| Trial | Wall time | Pi tokens | e2e tokens | Total tokens | Prompt-cache reads |',
  '| --- | ---: | ---: | ---: | ---: | ---: |',
  ...records.map((r) => `| ${r.id} | ${fmt(r.wallSeconds, 2)}s | ${fmt(r.pi.total)} | ${fmt(r.e2e.total)} | ${fmt(r.totalTokens)} | ${fmt(r.cacheReadTokens)} |`), '',
  '## Scope and limitations', '',
  '- This is an execution microbenchmark, not an app-development or full global-MEGAI-profile benchmark. Pi core uses the same native model/auth with bash only; context files, extensions, skills, templates and themes are disabled in both arms for the child process only. Global configuration is untouched.',
  '- Live Pi sees full accessible Playwright snapshots and can batch actions; e2e uses its built-in observation/action loop. Tool topology and policies differ by design. This does not isolate an intrinsic harness efficiency difference.',
  '- The e2e and saved-Playwright tests, fixture, and direct browser bridge were prepared before timing. No test-authoring or package-install cost is included in the trial table. Cold means empty e2e action-replay cache, not an empty provider prompt cache.',
  '- Fresh fixture state, cookies and browser instances per trial. Each cold/warm pair shares only that pair’s action recording. Runs were sequential and first-arm order alternated; provider cache state and service latency were not controlled.',
  '- Native e2e requests were audited as GPT-6.1-Sol with reasoning.effort=high. The SDK needs forceReasoning=true for this model ID. Both providers reported zero reasoning tokens on these trivial tasks; requested effort is not a claim that hidden reasoning occurred.',
  '- Small synthetic flow, n=3 per arm. No significance, production reliability, billing, security, mobile, visual design, or large-app claim.',
  '- Initial preparation had an output-path validation failure, a report-envelope parser error after a passed default-reasoning run, and an audit-parser error after one native response. These were not trials and were not silently rerun into the table. All raw setup evidence is retained; the audit-parser failure’s provider usage was lost by that failed wrapper, so setup token expenditure is not claimed exact.',
  `- The measured 12-trial matrix consumed ${fmt(report.matrixTokens)} provider-reported tokens. Parent preparation/research conversation and preflight tokens are additional and excluded; this is not the total cost of doing the investigation.`, '',
  '## Evidence', '',
  '`results.json` contains sanitized trial records, source checksums and raw-receipt SHA-256 hashes. Raw Pi JSONL, e2e reports, SDK request metadata/usage, frozen prompts and the exact measured source snapshot are retained privately outside Git. The original measured runner is preserved even though the delivered version separates metrics and namespaces replay paths for safe reruns.', '',
  'See `README.md` for reproduction and the Plane work item AS4DABD7BE-185 for the evidence location and delivery receipt.', '',
];
await fs.writeFile(path.join(output, 'results.md'), lines.join('\n'));
console.log('PASS: 12 accepted trials; Pi totals, nested receipts, models, high effort, cold misses and warm replays reconciled.');
console.log(JSON.stringify(summary, null, 2));
