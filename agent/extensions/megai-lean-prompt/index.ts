import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { ExtensionAPI } from '@mariozechner/pi-coding-agent';
import { SECTION, buildCatalog } from './lean-core.mjs';

// Shrinks the per-request skills listing (see lean-core.mjs). The per-run
// systemPromptOptions.skills are copies, so hiding entries here changes only this
// run's prompt: /skill:name commands, the skill registry and files are untouched.
// MEGAI_LEAN_PROMPT=0 disables it.
function loadConfig() {
  try {
    const here = dirname(fileURLToPath(import.meta.url));
    return JSON.parse(readFileSync(join(here, 'config.json'), 'utf8'));
  } catch {
    return {};
  }
}

export default function (pi: ExtensionAPI) {
  const config = loadConfig();
  pi.on('before_agent_start', (event: any) => {
    try {
      if (String(process.env.MEGAI_LEAN_PROMPT ?? '') === '0') return;
      const opts = event?.systemPromptOptions;
      if (!opts || opts.forceSystemPrompt || !Array.isArray(opts.skills)) return;
      // Pi lists skills only when a file reader exists; keep the catalog consistent.
      const tools: string[] = (opts.selectedTools ?? []).filter((t: string) => !(opts.hiddenTools ?? []).includes(t));
      if (!tools.includes('read') && !tools.includes('bash')) return;
      const catalog = buildCatalog(opts.skills, config);
      if (!catalog) return;
      for (const skill of opts.skills) {
        if (catalog.compact.has(skill.name)) skill.disableModelInvocation = true;
      }
      opts.sections = { ...(opts.sections ?? {}), [SECTION]: catalog.section };
    } catch {
      return; // fail open: the default full listing stays
    }
  });
}
