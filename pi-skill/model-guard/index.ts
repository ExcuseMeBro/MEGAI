import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const models = new Set([
  "openai-codex/gpt-6-astra",
  "openai-codex/gpt-5.6-luna",
  "openai-codex/gpt-5.6-sol",
  "openai-codex/gpt-5.6-terra",
]);
const thinking = (value: unknown) => value === "medium" || value === "high";
const object = (value: unknown): Record<string, unknown> | undefined =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : undefined;
const reason = "MEGAI subagents require Pi with an exact openai-codex model: gpt-6-astra, gpt-5.6-luna, gpt-5.6-sol or gpt-5.6-terra; explicit medium/high thinking. Use structured Paseo MCP calls, never a default, wildcard or another-model fallback.";

/** Tool-call guard, not an OS sandbox. Never rewrites a requested model or task. */
export function blocked(name: string, value: unknown): boolean {
  const input = object(value) ?? {};
  name = name.replace(/^functions\./, "");
  if (name === "mcpScript" || ["subagent", "subagents", "dispatch_agent"].includes(name)) return true;
  if (name === "bash" || name === "powershell") {
    // Route obvious agent CLI launches through inspectable MCP. This is not a
    // shell parser and cannot enforce against arbitrary scripts/OS processes.
    const command = typeof input.command === "string" ? input.command : "";
    return /(?:^|[\n;&|])\s*(?:\S*\/)?paseo\s+(?:(?:--json|--quiet|-q)\s+)*(?:run|agent\s+(?:run|create))\b/.test(command)
      || /(?:^|[\n;&|])\s*(?:\S*\/)?pi(?=\s)[^\n]*(?:--print\b|(?:^|\s)-p\b|--mode\s+(?:rpc|json)\b)/.test(command);
  }
  if (name === "mcp" || name === "mcp__paseo") {
    // Match the gateway's documented precedence. Discovery never launches.
    if (name === "mcp" && input.action) return false;
    if (typeof input.tool !== "string") return false;
    const tool = input.tool;
    const paseo = name === "mcp__paseo" || input.server === "paseo" || /^paseo[_/:]/.test(tool);
    if (!paseo) return false;
    name = `paseo_${tool.replace(/^paseo[_/:]/, "")}`;
    let args = input.args;
    if (typeof args === "string") {
      try { args = JSON.parse(args); } catch { return true; }
    }
    return blocked(name, args);
  }
  name = name.replace(/^paseo[/:]/, "paseo_");
  // Schedules can launch agents later, outside this tool-call preflight.
  if (["paseo_create_schedule", "paseo_update_schedule", "paseo_resume_schedule", "paseo_run_schedule_once"].includes(name)) return true;
  if (name === "paseo_create_agent") {
    const provider = input.provider;
    return typeof provider !== "string" || !provider.startsWith("pi/")
      || !models.has(provider.slice(3))
      || !thinking(object(input.settings)?.thinkingOptionId);
  }
  if (name === "paseo_update_agent") {
    const settings = object(input.settings);
    if (!settings) return input.settings !== undefined;
    if ("model" in settings && (typeof settings.model !== "string" || !models.has(settings.model)
      || !thinking(settings.thinkingOptionId))) return true;
    return "thinkingOptionId" in settings && !thinking(settings.thinkingOptionId);
  }
  return false;
}

export default function modelGuard(pi: ExtensionAPI) {
  pi.on("tool_call", event => {
    if (blocked(event.toolName, event.input)) return { block: true, reason };
  });
}
