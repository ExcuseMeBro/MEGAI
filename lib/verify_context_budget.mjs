#!/usr/bin/env node
// Confirm an installed context budget with the real native model loader.
// Offline: temporary auth/catalog paths, refresh disabled, no provider request.
import { existsSync, mkdtempSync, realpathSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { packageForExecutable } from './verify_headroom_activation.mjs';

export function packageRoot(executable) {
  if (process.env.PI_PACKAGE_ROOT) return process.env.PI_PACKAGE_ROOT;
  if (executable) return packageForExecutable(executable);
  throw new Error('Cannot locate the Pi package; set PI_PACKAGE_ROOT');
}

export async function budgetState(agentDir, expected, executable) {
  const { ModelRuntime } = await import(pathToFileURL(join(packageRoot(executable), 'dist/index.js')));
  const temporary = mkdtempSync(join(tmpdir(), 'pi-context-budget-'));
  try {
    const runtime = await ModelRuntime.create({
      modelsPath: join(agentDir, 'models.json'),
      authPath: join(temporary, 'auth.json'),
      modelsStorePath: join(temporary, 'catalog.json'),
      refreshOnCreate: false,
      allowModelNetwork: false,
    });
    if (runtime.getError()) throw new Error(`native model loader error: ${runtime.getError()}`);
    const observed = {};
    for (const [target, window] of Object.entries(expected)) {
      const index = target.indexOf('/');
      const model = runtime.getModel(target.slice(0, index), target.slice(index + 1));
      if (!model) throw new Error(`native loader does not know ${target}`);
      if (model.contextWindow !== window) {
        throw new Error(`${target} contextWindow is ${model.contextWindow}, expected ${window}`);
      }
      observed[target] = model.contextWindow;
    }
    return observed;
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) {
  const [agentDir, executable] = process.argv.slice(2);
  if (!agentDir || !existsSync(join(agentDir, 'models.json'))) {
    console.error('usage: verify_context_budget.mjs AGENT_DIR [PI_EXECUTABLE]');
    process.exit(1);
  }
  const raw = process.env.MEGAI_CONTEXT_BUDGET_EXPECTED;
  if (!raw) {
    console.error('MEGAI_CONTEXT_BUDGET_EXPECTED must hold the expected {target: window} JSON');
    process.exit(1);
  }
  budgetState(agentDir, JSON.parse(raw), executable).then((observed) => {
    console.log(Object.entries(observed).map(([target, window]) => `${target}=${window}`).join(' '));
  }).catch((error) => {
    console.error(`context budget verification failed: ${error.message}`);
    process.exit(1);
  });
}
