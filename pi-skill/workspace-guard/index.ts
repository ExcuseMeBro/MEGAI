import type { ExtensionAPI } from '@earendil-works/pi-coding-agent';
import { projectIdentity, validateWorkspace, validateWriteScope } from './identity.mjs';
import { realpath } from 'node:fs/promises';

const record = (value: unknown): Record<string, unknown> | undefined =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : undefined;
const mutations = new Set(['create_workspace', 'create_agent', 'create_project']);
const prefix = 'MEGAI workspace guard: ';
const route = 'Resolve identity with megai workspace --root CHECKOUT_OR_DIRECTORY. Git projects use structured Paseo create_workspace with isolation=worktree and the canonical projectId. Existing non-Git directory projects use isolation=local, then create_agent with the verified workspaceId and Pi provider. Set labels {"megai.access":"read-only"} for readers, or {"megai.access":"write","megai.writeScope":"relative/config-dir"} for an explicitly owned configuration scope. No new sibling project or clone.';

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
    if (identity.kind === 'directory') {
      if (name === 'paseo_create_workspace') {
        if (input.isolation !== 'local' || input.projectId !== identity.projectId
            || ['mode', 'worktreeSlug', 'branchName', 'baseBranch', 'branch', 'prNumber', 'forge'].some(key => key in input)
            || ('path' in input && (typeof input.path !== 'string' || await realpath(input.path) !== identity.root))) {
          return `${route} Expected directory projectId=${identity.projectId}, root=${identity.root}.`;
        }
      } else {
        const labels = record(input.labels);
        const access = labels?.['megai.access'];
        if ((access !== 'read-only' && access !== 'write')
            || typeof input.provider !== 'string' || !/^pi\/\S+$/.test(input.provider)
            || typeof input.workspaceId !== 'string' || !input.workspaceId) return route;
        await validateWorkspace(input.workspaceId, identity);
        if (access === 'write') await validateWriteScope(labels?.['megai.writeScope'], identity);
      }
    } else if (name === 'paseo_create_workspace') {
      if (input.isolation !== 'worktree' || input.projectId !== identity.projectId || 'path' in input
          || ('worktreeSlug' in input && (typeof input.worktreeSlug !== 'string' || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(input.worktreeSlug)))) {
        return `${route} Expected projectId=${identity.projectId}, primary=${identity.root}.`;
      }
    } else {
      if (typeof input.workspaceId !== 'string' || !input.workspaceId) return route;
      await validateWorkspace(input.workspaceId, identity);
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
