import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

test('live tgrep finds literal content and filename globs in a bounded external scope', () => {
  const root = mkdtempSync(join(tmpdir(), 'megai-tgrep-smoke-'));
  try {
    mkdirSync(join(root, 'src'));
    writeFileSync(join(root, 'src', 'probe.ts'), 'export const scopedSearch = true;\n');
    const content = execFileSync('tgrep', ['--no-index', '-nH', '-F', '--', 'scopedSearch', root], { encoding: 'utf8', timeout: 5000 });
    assert.match(content, /src\/probe\.ts:1:export const scopedSearch = true;/);
    const files = execFileSync('tgrep', ['--no-index', '--files', '--glob', '*.ts', '--', root], { encoding: 'utf8', timeout: 5000 });
    assert.match(files, /src\/probe\.ts/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
