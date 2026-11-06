// Run: node --experimental-strip-types --test pi-current/tests/lean-prompt.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const dir = join(root, 'agent/extensions/megai-lean-prompt');
const { SECTION, buildCatalog, trigger } = await import(join(dir, 'lean-core.mjs'));
const config = JSON.parse(readFileSync(join(dir, 'config.json'), 'utf8'));

const BASE = '/home/u/.pi/agent/skills';
const skill = (name, description, filePath = `${BASE}/${name}/SKILL.md`) =>
  ({ name, description, filePath, baseDir: filePath.replace(/\/SKILL\.md$/, ''), disableModelInvocation: false });
const long = (topic) => `This skill should be used when the user asks about "${topic}", "${topic} design", "${topic} trade-offs", or wants a reviewed plan for ${topic} with numbers, failure modes, alternatives and a migration path that the team can execute safely.`;

function fixture() {
  const list = [
    skill('security-audit', 'Security guidance and vulnerability review for codebases. Use for security questions.'),
    skill('pi-workflow', 'Track project changes in Brokan and deliver tested task branches to dev.'),
  ];
  for (let i = 0; i < 40; i++) list.push(skill(`topic-${String(i).padStart(2, '0')}`, long(`topic ${i}`)));
  list.push(skill('agentmemory-config', 'Use when configuring agentmemory.', '/opt/am/skills/agentmemory-config/SKILL.md'));
  list.push(skill('odd-layout', 'Odd file layout skill.', '/opt/x/odd/README-SKILL.md'));
  list.push({ ...skill('user-only', 'Only via /skill:user-only.'), disableModelInvocation: true });
  return list;
}

test('trigger drops boilerplate openers and keeps routing phrases', () => {
  assert.equal(trigger('This skill should be used when the user asks about "caching strategy", "cache invalidation".'), '"caching strategy", "cache invalidation".');
  assert.equal(trigger('Use when building toasts with Sonner.'), 'building toasts with Sonner.');
  const t = trigger(long('sharding'), 80);
  assert.ok(t.length <= 81 && t.endsWith('…'), t);
  assert.ok(t.startsWith('"sharding"'), t);
});

test('catalog keeps full entries for configured skills and compacts the rest', () => {
  const skills = fixture();
  const cat = buildCatalog(skills, { full: ['security-audit', 'pi-workflow'], limit: 140 });
  assert.ok(cat);
  assert.ok(!cat.compact.has('security-audit') && !cat.compact.has('pi-workflow'));
  assert.ok(!cat.compact.has('user-only'), 'already hidden skills stay hidden and unlisted');
  assert.equal(cat.compact.size, 42);
  for (const s of skills.filter((x) => cat.compact.has(x.name))) assert.ok(cat.section.includes(`- ${s.name}`), s.name);
  // Conventional layouts share one Path line per base; odd layouts carry their own path.
  assert.ok(cat.section.includes(`Path: ${BASE}/<name>/SKILL.md`));
  assert.ok(cat.section.includes('Path: /opt/am/skills/<name>/SKILL.md'));
  assert.ok(cat.section.includes('- odd-layout (/opt/x/odd/README-SKILL.md):'));
  assert.ok(!cat.section.includes('user-only'));
});

test('catalog is much smaller than the default listing', () => {
  const skills = fixture();
  const xml = skills.filter((s) => !s.disableModelInvocation).map((s) =>
    `  <skill>\n    <name>${s.name}</name>\n    <description>${s.description}</description>\n    <location>${s.filePath}</location>\n  </skill>`).join('\n');
  const cat = buildCatalog(skills, { full: ['security-audit', 'pi-workflow'], limit: 140 });
  assert.ok(cat.section.length < xml.length * 0.6, `${cat.section.length} vs ${xml.length}`);
});

test('few compactable skills: no change', () => {
  assert.equal(buildCatalog(fixture().slice(0, 5), { full: [], minSkills: 8 }), null);
  assert.equal(buildCatalog([], config), null);
});

async function run(opts, env = {}) {
  const saved = process.env.MEGAI_LEAN_PROMPT;
  if ('MEGAI_LEAN_PROMPT' in env) process.env.MEGAI_LEAN_PROMPT = env.MEGAI_LEAN_PROMPT; else delete process.env.MEGAI_LEAN_PROMPT;
  try {
    let handler;
    const mod = await import(join(dir, 'index.ts'));
    mod.default({ on: (name, fn) => { if (name === 'before_agent_start') handler = fn; } });
    handler({ type: 'before_agent_start', messageType: 'user', prompt: 'x', systemPromptOptions: opts });
    return opts;
  } finally {
    if (saved === undefined) delete process.env.MEGAI_LEAN_PROMPT; else process.env.MEGAI_LEAN_PROMPT = saved;
  }
}
const options = (extra = {}) => ({ cwd: '/w', selectedTools: ['read', 'bash', 'edit', 'write'], hiddenTools: [], sections: { other: 'keep' }, skills: fixture(), ...extra });

test('extension hides compacted skills for this run and adds the catalog section', async () => {
  const opts = await run(options());
  const hidden = opts.skills.filter((s) => s.disableModelInvocation).map((s) => s.name);
  for (const name of config.full) assert.ok(!hidden.includes(name), name);
  assert.ok(hidden.includes('topic-00') && hidden.includes('agentmemory-config'));
  assert.equal(opts.sections.other, 'keep');
  assert.match(opts.sections[SECTION], /- topic-00: /);
});

test('extension is a no-op when disabled, forced, or without a file reader', async () => {
  for (const [opts, env] of [
    [options(), { MEGAI_LEAN_PROMPT: '0' }],
    [options({ forceSystemPrompt: 'custom' }), {}],
    [options({ selectedTools: ['codemode'] }), {}],
    [options({ selectedTools: ['read', 'codemode'], hiddenTools: ['read'] }), {}],
  ]) {
    const out = await run(opts, env);
    assert.equal(out.skills.filter((s) => s.disableModelInvocation).length, 1, 'only the pre-hidden skill');
    assert.equal(out.sections[SECTION], undefined);
  }
});

test('extension fails open on malformed input', async () => {
  const opts = await run({ cwd: '/w', selectedTools: ['read'], skills: [null, 42, { name: 'x' }], sections: {} });
  assert.equal(opts.sections[SECTION], undefined);
});
