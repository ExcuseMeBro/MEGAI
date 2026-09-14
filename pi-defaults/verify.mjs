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
const metadata = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8'));
if (metadata.name !== '@earendil-works/pi-coding-agent' || metadata.version !== '0.85.1') {
  throw new Error('PATH must select @earendil-works/pi-coding-agent 0.85.1');
}
const agentDir = join(homedir(), '.pi/agent');
if (process.env.PI_CODING_AGENT_DIR && realpathSync(process.env.PI_CODING_AGENT_DIR) !== realpathSync(agentDir)) {
  throw new Error('Custom PI_CODING_AGENT_DIR is unsupported by the clean default profile');
}
const { DefaultResourceLoader } = await import(pathToFileURL(join(packageRoot, 'dist/index.js')).href);
const loader = new DefaultResourceLoader({ cwd: process.cwd(), agentDir });
await loader.reload();
const loaded = loader.getExtensions();
const tools = loaded.extensions.flatMap(e => [...e.tools.keys()]);
const commands = loaded.extensions.flatMap(e => [...e.commands.keys()]);
const skills = loader.getSkills();
const requiredTools = ['mcp', 'subagent', 'web_search', 'fetch_content', 'headroom_retrieve', 'headroom_memory'];
const requiredSkills = ['pi-workflow', 'using-superpowers', 'test-driven-development', 'ponytail', 'openspec-propose', 'openspec-apply-change'];
const missing = [...requiredTools.filter(t => !tools.includes(t)), ...requiredSkills.filter(s => !skills.skills.some(v => v.name === s))];
if (!commands.includes('ponytail')) missing.push('/ponytail');
const report = { extensions: loaded.extensions.map(e => e.path), tools, skills: skills.skills.map(s => s.name), errors: loaded.errors, diagnostics: skills.diagnostics, missing };
console.log(JSON.stringify(report, null, 2));
process.exit(loaded.errors.length || skills.diagnostics.length || missing.length ? 1 : 0);
