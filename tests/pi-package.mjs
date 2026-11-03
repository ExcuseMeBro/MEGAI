// Locate a loadable native Pi package (@earendil-works/pi-coding-agent with dist/) for tests.
// Order: PI_PACKAGE_ROOT, the package beside the `pi` executable, then bun/npm globals.
// A compiled Pi (e.g. Pi-Bolt) ships package.json without dist/, so it is skipped.
// Importing this module sets PI_PACKAGE_ROOT when it was unset and a package is found.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, realpathSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';

const NAME = '@earendil-works/pi-coding-agent';

function loadable(root) {
  try {
    return JSON.parse(readFileSync(join(root, 'package.json'), 'utf8')).name === NAME
      && existsSync(join(root, 'dist/index.js'));
  } catch { return false; }
}

function quiet(command, args) {
  try { return execFileSync(command, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 10000 }).trim(); }
  catch { return ''; }
}

function besideExecutable() {
  const executable = quiet('which', ['pi']);
  if (!executable) return [];
  const found = [];
  for (let dir = dirname(realpathSync(executable)); ; dir = dirname(dir)) {
    found.push(dir);
    if (dirname(dir) === dir) return found;
  }
}

export function piPackageRoot() {
  const candidates = [
    process.env.PI_PACKAGE_ROOT,
    ...besideExecutable(),
    join(homedir(), '.bun/install/global/node_modules', NAME),
    quiet('npm', ['root', '-g']) && join(quiet('npm', ['root', '-g']), NAME),
  ].filter(Boolean);
  const root = candidates.find(loadable);
  if (!root) throw new Error(`No loadable ${NAME} package (with dist/) found; set PI_PACKAGE_ROOT`);
  return root;
}

if (!process.env.PI_PACKAGE_ROOT) {
  try { process.env.PI_PACKAGE_ROOT = piPackageRoot(); } catch { /* tests report the missing package */ }
}
