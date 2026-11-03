// packageForExecutable: npm Pi beside its executable, or a compiled Pi (Pi-Bolt) whose
// loader comes only from a global install of the exact same version.
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const verifier = new URL('../lib/verify_headroom_activation.mjs', import.meta.url).href;
const NAME = '@earendil-works/pi-coding-agent';

function pkg(dir, version, { dist }) {
  mkdirSync(join(dir, 'dist'), { recursive: true });
  writeFileSync(join(dir, 'package.json'), JSON.stringify({ name: NAME, version }));
  if (dist) writeFileSync(join(dir, 'dist/index.js'), 'export {};\n');
  writeFileSync(join(dir, 'pi'), '#!/bin/sh\n', { mode: 0o755 });
  return join(dir, 'pi');
}

function resolveWith(home, executable) {
  const script = `import(${JSON.stringify(verifier)}).then(m => process.stdout.write(m.packageForExecutable(${JSON.stringify(executable)})))`;
  // No npm on PATH: only the HOME-scoped bun global is a candidate.
  return execFileSync(process.execPath, ['--input-type=module', '-e', script],
    { encoding: 'utf8', env: { HOME: home, MEGAI_HOME: join(home, '.megai'), PATH: '/usr/bin:/bin' }, stdio: ['ignore', 'pipe', 'pipe'] });
}

test('package beside the executable wins; compiled Pi needs an exact-version global loader', () => {
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'pi-package-exec-')));
  try {
    const npmPi = pkg(join(root, 'npm-pi'), '1.4.0', { dist: true });
    assert.equal(resolveWith(join(root, 'home'), npmPi), join(root, 'npm-pi'));

    const compiled = pkg(join(root, 'pi-bolt'), '1.4.0', { dist: false });
    const global = join(root, 'home/.bun/install/global/node_modules', NAME);
    assert.throws(() => resolveWith(join(root, 'home'), compiled), /Compiled Pi 1\.4\.0 has no loader/);

    pkg(global, '1.5.0', { dist: true });
    assert.throws(() => resolveWith(join(root, 'home'), compiled), /Compiled Pi 1\.4\.0 has no loader/,
      'a different global version must fail closed');

    const loader = join(root, 'home/.megai/pi-loader/1.4.0/node_modules', NAME);
    pkg(loader, '1.4.0', { dist: true });
    assert.equal(resolveWith(join(root, 'home'), compiled), loader, 'private exact-version loader is used');
    rmSync(loader, { recursive: true, force: true });

    pkg(global, '1.4.0', { dist: true });
    assert.equal(resolveWith(join(root, 'home'), compiled), global);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
