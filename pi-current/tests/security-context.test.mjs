import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';

const drift = fileURLToPath(new URL('../agent/skills/security-context/scripts/detect-drift.mjs', import.meta.url));

test('detect-drift: missing = 1, clean = 0, boundary or manifest change = 2, read-only', t => {
  const repo = mkdtempSync(join(tmpdir(), 'secctx-'));
  t.after(() => rmSync(repo, { recursive: true, force: true }));
  const git = (...a) => execFileSync('git', a, { cwd: repo, encoding: 'utf8' }).trim();
  const run = () => spawnSync(process.execPath, [drift, repo], { encoding: 'utf8' });
  git('init', '-q'); git('config', 'user.email', 't@example.invalid'); git('config', 'user.name', 't');
  mkdirSync(join(repo, 'src/auth'), { recursive: true });
  writeFileSync(join(repo, 'src/auth/jwt.ts'), 'export {}\n'); writeFileSync(join(repo, 'README.md'), 'x\n');
  git('add', '.'); git('commit', '-qm', 'base');
  assert.equal(run().status, 1, 'missing file');
  const sha = git('rev-parse', 'HEAD');
  writeFileSync(join(repo, 'SECURITY_CONTEXT.md'), `---\nschema_version: 1\nvisibility: private\nlast_synced_commit: ${sha}\n---\n- Use \`verifyJwt\` (\`src/auth/jwt.ts\`)\n`);
  writeFileSync(join(repo, 'AGENTS.md'), '## Security Context\n\nRead SECURITY_CONTEXT.md before editing `src/auth/**`.\n');
  assert.equal(run().status, 0, 'no commits after sync');
  writeFileSync(join(repo, 'README.md'), 'y\n'); git('commit', '-qam', 'docs');
  const clean = run(); assert.equal(clean.status, 0, clean.stdout); assert.match(clean.stdout, /"status":"clean"/);
  writeFileSync(join(repo, 'src/auth/jwt.ts'), 'export const x = 1\n'); git('commit', '-qam', 'auth');
  const d = run(); assert.equal(d.status, 2); assert.match(d.stdout, /src\/auth\/jwt\.ts/);
  assert.equal(git('status', '--porcelain'), '?? AGENTS.md\n?? SECURITY_CONTEXT.md'.trim(), 'script wrote nothing');
});
