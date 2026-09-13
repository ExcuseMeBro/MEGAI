#!/usr/bin/env node
// Resolve actual Pi resources; never infer activation from file existence.
import { realpathSync, existsSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { dirname, join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const canonical = (path) => { try { return realpathSync(path); } catch { return resolve(path); } };

/**
 * Local core paths the opt-in max profile may legitimately activate.
 * Only a receipt-owned sidecar whose own hash matches, plus matching per-file core
 * receipts, qualify; an unowned, modified or foreign caveman/legacy resource, or a
 * removed/modified sidecar receipt, still fails the check.
 */
export function ownedTokenProfileCores(agentDir) {
  try {
    const megai = process.env.MEGAI_HOME || join(homedir(), '.megai');
    const sidecar = join(agentDir, 'megai-token-profile.json');
    const sidecarData = readFileSync(sidecar);
    const receipt = JSON.parse(readFileSync(join(megai, 'slim-wiring.json'), 'utf8'));
    if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) return new Set();
    if (receipt[sidecar] !== createHash('sha256').update(sidecarData).digest('hex')) return new Set();
    const profile = JSON.parse(sidecarData.toString('utf8'));
    if (profile?.schema !== 1 || profile?.profile !== 'max') return new Set();
    const allowed = new Set();
    for (const name of ['caveman', 'ponytail']) {
      const file = join(agentDir, 'skills', name, 'SKILL.md');
      const digest = createHash('sha256').update(readFileSync(file)).digest('hex');
      if (receipt[file] === digest) allowed.add(canonical(file));
    }
    return allowed;
  } catch {
    return new Set();
  }
}

export function packageForExecutable(executable) {
  let directory = dirname(realpathSync(executable));
  for (;;) {
    const manifest = join(directory, 'package.json');
    if (existsSync(manifest)) {
      const name = JSON.parse(readFileSync(manifest, 'utf8')).name;
      if (typeof name === 'string' && name.endsWith('/pi-coding-agent')
          && existsSync(join(directory, 'dist/index.js'))) return directory;
    }
    const parent = dirname(directory);
    if (parent === directory) throw new Error('Cannot locate the Pi package from its executable; set PI_PACKAGE_ROOT');
    directory = parent;
  }
}

export async function activation(packageRoot, options = {}) {
  const { DefaultResourceLoader } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')));
  const agentDir = options.agentDir ?? process.env.PI_CODING_AGENT_DIR ?? join(homedir(), '.pi/agent');
  const loader = new DefaultResourceLoader({ cwd: process.cwd(), agentDir, ...options });
  await loader.reload();
  const loaded = loader.getExtensions();
  if (loaded.errors.length) throw new Error('Pi extension load errors: ' + loaded.errors.map(e => `${e.path}: ${e.error}`).join('; '));
  const legacy = /(?:^|[/\\])(?:rtk|caveman|agent[-_]?memory|megai-memory)(?:$|[/\\.])/i;
  const ownedCores = ownedTokenProfileCores(agentDir);
  const resources = [...loaded.extensions.map(e => e.resolvedPath), ...loader.getSkills().skills.map(s => s.filePath)];
  const retired = resources.filter(path => legacy.test(path) && !ownedCores.has(canonical(path)));
  if (retired.length) throw new Error('Retired Pi resources remain active; reconcile: ' + retired.join(', '));
  return loaded.extensions.some(extension => extension.tools.has('headroom_retrieve') && extension.tools.has('headroom_memory'));
}

if (process.argv[1] && realpathSync(process.argv[1]) === realpathSync(fileURLToPath(import.meta.url))) {
  const deadline = setTimeout(() => {
    process.stderr.write('Headroom activation timed out.\n', () => process.exit(1));
  }, 30000);
  try {
    const packageRoot = process.env.PI_PACKAGE_ROOT || packageForExecutable(process.argv[2]);
    process.env.PI_OFFLINE = '1'; // Verification must not install/update unrelated packages.
    const active = await activation(packageRoot, { cwd: process.cwd() });
    clearTimeout(deadline);
    const message = active ? 'Headroom active in the fresh Pi resource loader.' : 'Headroom INACTIVE: Pi resource selections exclude it. Selections preserved; runtime installation is not activation.';
    // This is a snapshot process, not a Pi session. User extensions may register
    // background timers during loading; they must not keep verification alive.
    process.stdout.write(message + '\n', () => process.exit(active ? 0 : 2));
  } catch (error) {
    clearTimeout(deadline);
    process.stderr.write('Headroom activation unverified: ' + error.message + '\n', () => process.exit(1));
  }
}
