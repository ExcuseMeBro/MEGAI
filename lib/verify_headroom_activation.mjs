#!/usr/bin/env node
// Resolve actual Pi resources; never infer activation from file existence.
import { realpathSync, existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

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
  const loader = new DefaultResourceLoader({ cwd: process.cwd(),
    agentDir: process.env.PI_CODING_AGENT_DIR || join(homedir(), '.pi/agent'), ...options });
  await loader.reload();
  const loaded = loader.getExtensions();
  if (loaded.errors.length) throw new Error('Pi extension load errors: ' + loaded.errors.map(e => `${e.path}: ${e.error}`).join('; '));
  const legacy = /(?:^|[/\\])(?:rtk|caveman|agent[-_]?memory|megai-memory)(?:$|[/\\.])/i;
  const resources = [...loaded.extensions.map(e => e.resolvedPath), ...loader.getSkills().skills.map(s => s.filePath)];
  const retired = resources.filter(path => legacy.test(path));
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
