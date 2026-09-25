#!/usr/bin/env node
import { realpathSync, existsSync, readFileSync, accessSync, constants } from 'node:fs';
import { dirname, join, delimiter } from 'node:path';
import { homedir } from 'node:os';
import { pathToFileURL } from 'node:url';

const command = process.env.PATH.split(delimiter).map(p => join(p, 'pi')).find(p => { try { accessSync(p, constants.X_OK); return true; } catch { return false; } });
if (!command) throw new Error('Pi CLI missing');
let packageRoot = dirname(realpathSync(command));
while (!existsSync(join(packageRoot, 'package.json'))) {
  const parent = dirname(packageRoot);
  if (parent === packageRoot) throw new Error('Cannot find Pi package');
  packageRoot = parent;
}
const agentDir = join(homedir(), '.pi/agent');
if (process.env.PI_CODING_AGENT_DIR && realpathSync(process.env.PI_CODING_AGENT_DIR) !== realpathSync(agentDir)) {
  throw new Error('Custom PI_CODING_AGENT_DIR is unsupported by the clean default profile');
}
// The profile installs the newest Pi and records what it resolved; the check compares
// PATH against that record instead of a version pinned here, which only went stale.
const metadata = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
const manifestPath = join(agentDir, 'defaults/manifest.json');
const recorded = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')).pi : undefined;
if (metadata.name !== '@earendil-works/pi-coding-agent'
    || (typeof recorded === 'string' && metadata.version !== recorded)) {
  throw new Error(`PATH must select @earendil-works/pi-coding-agent${typeof recorded === 'string' ? ` ${recorded}` : ''}, found ${metadata.name}@${metadata.version}; re-run the MEGAI Pi install`);
}
const { DefaultResourceLoader } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')).href);
const loader = new DefaultResourceLoader({ cwd: process.cwd(), agentDir });
await loader.reload();
const loaded = loader.getExtensions();
const tools = loaded.extensions.flatMap(e => [...e.tools.keys()]);
const commands = loaded.extensions.flatMap(e => [...e.commands.keys()]);
const skills = loader.getSkills();
const prompts = loader.getPrompts();
const promptNames = prompts.prompts.map(p => p.name);
const engineeringOnly = process.argv.includes('--engineering-only');
const requiredTools = engineeringOnly ? [] : ['mcp', 'web_search', 'fetch_content', 'headroom_retrieve', 'headroom_memory'];
const removedTools = ['subagent'];
const requiredSkills = ['pi-workflow', 'codebase-design', 'diagnosing-bugs', 'tdd', 'code-review'];
const requiredPrompts = engineeringOnly ? [] : ['factory', 'mdev', 'prdev', 'rwbrowser'];
const policy = existsSync(join(agentDir, 'AGENTS.md')) ? readFileSync(join(agentDir, 'AGENTS.md'), 'utf8') : '';
const missing = [...requiredTools.filter(t => !tools.includes(t)), ...requiredSkills.filter(s => !skills.skills.some(v => v.name === s))];
for (const name of requiredPrompts) if (!promptNames.includes(name)) missing.push(`/${name}`);
for (const name of ['ponytail', 'using-superpowers']) {
  if (skills.skills.some(s => s.name === name) || commands.includes(name)) missing.push(`retired resource: ${name}`);
}
for (const name of requiredSkills) {
  if (skills.skills.filter(s => s.name === name).length > 1) missing.push(`duplicate skill: ${name}`);
}
if (skills.skills.some(s => s.name.startsWith('openspec-')) || promptNames.some(n => n.startsWith('opsx-'))) missing.push('retired OpenSpec resources');
for (const name of removedTools) if (tools.includes(name)) missing.push(`removed tool: ${name}`);
if (!policy.includes('native Paseo agents')) missing.push('AGENTS.md: native Paseo policy');
if (policy.includes('Use pi-subagents')) missing.push('AGENTS.md: removed delegation policy');
const report = { extensions: loaded.extensions.map(e => e.path), tools, skills: skills.skills.map(s => s.name), prompts: promptNames, errors: loaded.errors, diagnostics: [...skills.diagnostics, ...prompts.diagnostics], missing };
console.log(JSON.stringify(report, null, 2));
process.exit(loaded.errors.length || skills.diagnostics.length || prompts.diagnostics.length || missing.length ? 1 : 0);
