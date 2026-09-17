#!/usr/bin/env node
// Read-only native Pi resource-loader probe for skill-profile fixtures.
// Prints the skill directory names the real loader resolves; never writes.
import { basename, dirname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (!key.startsWith('--')) throw new Error(`unexpected argument: ${key}`);
    const value = argv[index + 1];
    if (value === undefined) throw new Error(`${key} needs a value`);
    args[key.slice(2)] = value;
    index += 1;
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
for (const required of ['package-root', 'agent-dir', 'cwd']) {
  if (!args[required]) throw new Error(`--${required} is required`);
}
const trusted = args.trusted === '1' || args.trusted === 'true';
const packageRoot = resolve(args['package-root']);
const { DefaultResourceLoader, SettingsManager } = await import(
  pathToFileURL(join(packageRoot, 'dist/index.js'))
);
const agentDir = resolve(args['agent-dir']);
const cwd = resolve(args.cwd);
const settingsManager = SettingsManager.create(cwd, agentDir, { projectTrusted: trusted });
const loader = new DefaultResourceLoader({ cwd, agentDir, settingsManager });
await loader.reload();
const loaded = loader.getSkills();
const skills = loaded.skills.map((skill) => basename(dirname(skill.filePath)));
const diagnostics = loaded.diagnostics.map((diagnostic) => diagnostic.message);
process.stdout.write(`${JSON.stringify({ skills, diagnostics })}\n`);
