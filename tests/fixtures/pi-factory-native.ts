// Explicit offline extension loaded only by the isolated native Pi RPC test.
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';

export default async function (pi: ExtensionAPI) {
  const root = process.env.PI_PACKAGE_ROOT;
  if (!root || !process.env.PI_FACTORY_TEST_BASE || process.env.MEGAI_FACTORY_PREP_WORKER !== '1') throw new Error('Isolated fixture required');
  const { fauxProvider, fauxAssistantMessage } = await import(pathToFileURL(join(dirname(root), 'pi-ai/dist/index.js')).href);
  const faux = fauxProvider({ models: [{ id: 'fixture', reasoning: true }] });
  pi.registerProvider(faux.provider);
  faux.setResponses([() => {
    writeFileSync('native-candidate.txt', 'Prepared by the native RPC fixture.\n');
    execFileSync('git', ['add', 'native-candidate.txt']);
    execFileSync('git', ['commit', '-qm', 'Native RPC candidate']);
    return fauxAssistantMessage('Fixture candidate prepared.\nFACTORY_READY');
  }]);
}
