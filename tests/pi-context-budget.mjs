// Offline native-model configuration regression; no provider request or user auth.
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
const packageRoot = process.env.PI_PACKAGE_ROOT;
assert.ok(packageRoot, 'Set PI_PACKAGE_ROOT to the installed native Pi package');
const { ModelRuntime, shouldCompact, DEFAULT_COMPACTION_SETTINGS } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')));
const source = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const modelsPath = process.argv[2] || join(source, 'pi-skill/context-budget.models.json');
const temporary = mkdtempSync(join(tmpdir(), 'pi-context-budget-'));
try {
  const options = { authPath: join(temporary, 'auth.json'), modelsStorePath: join(temporary, 'catalog.json'),
    refreshOnCreate: false, allowModelNetwork: false };
  const baseline = await ModelRuntime.create({ ...options, modelsPath: null });
  const tuned = await ModelRuntime.create({ ...options, modelsPath });
  assert.equal(baseline.getError(), undefined);
  assert.equal(tuned.getError(), undefined);
  const settings = DEFAULT_COMPACTION_SETTINGS;
  assert.equal(settings.keepRecentTokens, 20000, 'Retain native recent-history policy');
  for (const id of ['gpt-6-astra', 'gpt-5.6-sol']) {
    const before = baseline.getModel('openai-codex', id);
    const after = tuned.getModel('openai-codex', id);
    assert.ok(before && after, 'Required native model must exist: ' + id);
    assert.equal(shouldCompact(140000, before.contextWindow, settings), false, 'Baseline reproduces late compaction');
    assert.equal(shouldCompact(140000, after.contextWindow, settings), true, '140k history must trigger native compaction');
    assert.equal(after.contextWindow, 65536);
    // Native override composition materializes an absent samplingParams as undefined.
    assert.deepEqual({ ...after, contextWindow: before.contextWindow },
      { ...before, samplingParams: before.samplingParams }, 'Only context budget changes; preserve all other model metadata');
    assert.equal(shouldCompact(49152, after.contextWindow, settings), false);
    assert.equal(shouldCompact(49153, after.contextWindow, settings), true);
    assert.equal(shouldCompact(140000, after.contextWindow, { ...settings, enabled: false }), false, 'Explicit opt-out wins');
    console.log(`${id}: native trigger ${before.contextWindow - settings.reserveTokens} -> ${after.contextWindow - settings.reserveTokens}; 140k false -> true; metadata/retention/opt-out preserved`);
  }
  assert.deepEqual(tuned.getModels().map(m => `${m.provider}/${m.id}`).sort(), baseline.getModels().map(m => `${m.provider}/${m.id}`).sort(), 'No model added or removed');
  for (const before of baseline.getModels()) {
    if (before.provider === 'openai-codex' && ['gpt-6-astra', 'gpt-5.6-sol'].includes(before.id)) continue;
    assert.deepEqual(tuned.getModel(before.provider, before.id), before, 'Other model unchanged');
  }
  console.log('PASS: native configuration/threshold regression only; not an end-to-end latency, cost or summary-quality benchmark');
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
