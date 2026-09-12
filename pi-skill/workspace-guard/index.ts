import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { projectIdentity, validateWorkspace, validateWriteScope, validateWorktreeSource } from './identity.mjs';
import { realpath } from 'node:fs/promises';

const record = (value: unknown): Record<string, unknown> | undefined =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : undefined;
const mutations = new Set(['create_workspace', 'create_agent', 'create_project']);
const prefix = 'MEGAI workspace guard: ';
const route = 'Resolve the existing folder with megai workspace --root FOLDER. Use one umbrella project/task identity. Git writers use structured Paseo create_workspace with isolation=worktree, that projectId and an absolute path to each primary component repository; use the same task branch/slug from dev in every affected repo. Local workspaces are for coordination/readers and scoped non-Git configuration writers. Pass the verified workspaceId and Pi provider to create_agent; local labels declare read-only or write with a relative megai.writeScope. No child project registration or clone. Follow agent-worktree-lifecycle for all-repo acceptance, dev delivery and separately approved main promotion; labels are not a sandbox or lock.';

/** Preflight only: never rewrite a call, create a project, or touch registries. */
export async function blocked(toolName: string, value: unknown, cwd: string): Promise<string | undefined> {
  let name = toolName.replace(/^functions\./, '').replace(/-/g, '_');
  const input = record(value) ?? {};
  if (name === 'mcpScript') return route;
  if (name === 'multi_tool_use.parallel') {
    if (!Array.isArray(input.tool_uses)) return route;
    for (const call of input.tool_uses) {
      const item = record(call);
      if (!item || typeof item.recipient_name !== 'string') return route;
      const reason = await blocked(item.recipient_name, item.parameters, cwd);
      if (reason) return reason;
    }
    return;
  }
  if (name === 'bash' || name === 'powershell') {
    const command = typeof input.command === 'string' ? input.command : '';
    // Deliberately not a shell parser or OS sandbox. Recognized direct creation
    // goes through structured MCP; arbitrary scripts/external clients are outside.
    if (/(?:^|[\n;&|])\s*(?:\S*\/)?git\s+(?:-C\s+(?:"[^"]*"|'[^']*'|\S+)\s+)?(?:worktree\s+add|clone)\b/.test(command)
        || /(?:^|[\n;&|])\s*(?:\S*\/)?paseo\s+(?:(?:--json|--quiet|-q)\s+)*(?:clone|(?:project|workspace)\s+create)\b/.test(command)) return route;
    return;
  }
  if (name === 'mcp' || name === 'mcp__paseo') {
    if (name === 'mcp' && input.action) return;
    if (typeof input.tool !== 'string') return;
    const tool = input.tool.replace(/-/g, '_');
    const paseo = name === 'mcp__paseo' || input.server === 'paseo' || /^paseo[_/:]/.test(tool)
      || (!input.server && mutations.has(tool));
    if (!paseo) return;
    let args = input.args;
    if (typeof args === 'string') {
      try { args = JSON.parse(args); } catch { return route; }
    }
    return blocked(`paseo_${tool.replace(/^paseo[_/:]/, '')}`, args, cwd);
  }
  name = name.replace(/^paseo[/:]/, 'paseo_');
  if (mutations.has(name)) name = `paseo_${name}`;
  if (!['paseo_create_workspace', 'paseo_create_agent', 'paseo_create_project'].includes(name)) return;
  if (name === 'paseo_create_project') return route;
  try {
    const identity = await projectIdentity(cwd);
    if (name === 'paseo_create_workspace') {
      if (input.isolation === 'local') {
        if (input.projectId !== identity.projectId
            || ['mode', 'worktreeSlug', 'branchName', 'baseBranch', 'branch', 'prNumber', 'forge'].some(key => key in input)
            || ('path' in input && (typeof input.path !== 'string' || await realpath(input.path) !== identity.root))) {
          return `${route} Expected projectId=${identity.projectId}, folder=${identity.root}.`;
        }
      } else {
        if (input.isolation !== 'worktree' || input.projectId !== identity.projectId
            || ('worktreeSlug' in input && (typeof input.worktreeSlug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(input.worktreeSlug)))) return route;
        await validateWorktreeSource(input.path ?? identity.root, identity);
      }
    } else {
      if (typeof input.workspaceId !== 'string' || !input.workspaceId
          || typeof input.provider !== 'string' || !/^pi\/\S+$/.test(input.provider)) return route;
      const mode = await validateWorkspace(input.workspaceId, identity);
      if (mode === 'local') {
        const labels = record(input.labels);
        const access = labels?.['megai.access'];
        if (access !== 'read-only' && access !== 'write') return route;
        if (access === 'write') await validateWriteScope(labels?.['megai.writeScope'], identity);
      }
    }
  } catch (error) {
    return `${error instanceof Error ? error.message : 'Identity lookup failed'}. ${route}`;
  }
}

export default function workspaceGuard(pi: ExtensionAPI) {
  pi.on('tool_call', async (event, ctx) => {
    const reason = await blocked(event.toolName, event.input, ctx.cwd);
    if (reason) return { block: true, reason: prefix + reason };
  });
}
