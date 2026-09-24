/**
 * MEGAI role routing context.
 *
 * Appends the configured role identities and bounded routing rules to the current
 * turn's system prompt. It reads only the global `megai-roles.json` on each prompt,
 * validates every rendered field, and never changes models, tools, or session state.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { closeSync, constants, fstatSync, openSync, readSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const MAX_CONFIG_BYTES = 64 * 1024;
const ROLE_KEYS = ["planner", "scout", "worker", "reviewer"] as const;
const THINKING_LEVELS = new Set(["off", "minimal", "low", "medium", "high", "xhigh", "max"]);
const PROVIDER = /^[A-Za-z0-9._:-]{1,64}$/;
const MODEL = /^[A-Za-z0-9._:/-]{1,96}$/;
const DEEPSEEK_FLASH = "deepseek/deepseek-flash";
const ELIGIBLE = new Set(["planner", "scout", "worker"]);
const FALLBACK = `${DEEPSEEK_FLASH} -> minimax/MiniMax-M3 -> openai-codex/gpt-6-luna`;
const BLOCKED =
  "\n\nMEGAI role context BLOCKED: the global megai-roles.json is unreadable or " +
  "invalid. Continue only with explicit user model choices and current evidence; do " +
  "not guess role routing or expose raw configuration.\n";

type Role = { provider: string; model: string; thinking: string };
type Config = { preset?: string; workerExecutor?: "antigravity_delegate"; roles: Record<string, Role> };
type Read = { kind: "missing" } | { kind: "invalid" } | { kind: "data"; text: string };

const record = (value: unknown): Record<string, unknown> | undefined =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown> : undefined;

/** Bounded read of a regular file. Never follows a symlink or blocks on a FIFO. */
function readConfig(path: string): Read {
  let fd: number;
  try {
    fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  } catch (error) {
    return (error as NodeJS.ErrnoException).code === "ENOENT" ? { kind: "missing" } : { kind: "invalid" };
  }
  try {
    const stat = fstatSync(fd);
    if (!stat.isFile() || stat.size > MAX_CONFIG_BYTES) return { kind: "invalid" };
    const buffer = Buffer.alloc(MAX_CONFIG_BYTES);
    let total = 0;
    while (total < MAX_CONFIG_BYTES) {
      const read = readSync(fd, buffer, total, MAX_CONFIG_BYTES - total, total);
      if (read <= 0) break;
      total += read;
    }
    return { kind: "data", text: buffer.subarray(0, total).toString("utf8") };
  } catch {
    return { kind: "invalid" };
  } finally {
    closeSync(fd);
  }
}

/** Accept schema 1, the supported presets and four role identities; custom
 * directories and a missing preset are fine. */
function parseConfig(text: string): Config | undefined {
  let value: unknown;
  try { value = JSON.parse(text); } catch { return undefined; }
  const config = record(value);
  const roles = record(config?.roles);
  if (!config || config.schema !== 1 || !roles) return undefined;
  if ("preset" in config && config.preset !== "economy" && config.preset !== "antigravity") return undefined;
  if (config.workerExecutor !== undefined &&
      (config.preset !== "antigravity" || config.workerExecutor !== "antigravity_delegate")) return undefined;
  const keys = Object.keys(roles);
  if (keys.length !== ROLE_KEYS.length || !ROLE_KEYS.every((key) => keys.includes(key))) return undefined;
  const parsed: Record<string, Role> = {};
  for (const key of ROLE_KEYS) {
    const role = record(roles[key]);
    const { provider, model, thinking } = role ?? {};
    if (typeof provider !== "string" || !PROVIDER.test(provider)) return undefined;
    if (typeof model !== "string" || !MODEL.test(model)) return undefined;
    if (typeof thinking !== "string" || !THINKING_LEVELS.has(thinking)) return undefined;
    parsed[key] = { provider, model, thinking };
  }
  return {
    preset: typeof config.preset === "string" ? config.preset : undefined,
    workerExecutor: config.workerExecutor === "antigravity_delegate" ? config.workerExecutor : undefined,
    roles: parsed,
  };
}

function render(config: Config): string {
  const identity = (role: Role) => `${role.provider}/${role.model}`;
  const roles = ROLE_KEYS.map((key) => `- ${key}: ${identity(config.roles[key])} (${config.roles[key].thinking})`);
  const parts = [
    "MEGAI role context (from megai-roles.json; runtime guidance only, not " +
      "automatic dispatch, enforcement, an allowlist or a sandbox):",
    `Configured roles:\n${roles.join("\n")}`,
    "The parent keeps its chosen model, and explicit user or task model choices " +
      "override this context. Every delegated role is a leaf: planner, scout, worker " +
      "and any fallback worker never delegate, and a worker or fallback worker does " +
      "not re-delegate its assigned implementation. The reviewer follows its " +
      "configured read-only role and does not delegate to the worker.",
  ];
  if (config.preset === "economy") {
    parts.push(
      "Parent-only economy routing: the parent routes substantial bounded implementation " +
        "to ONE configured worker instead of doing it in GPT; keep trivial or read-only " +
        "work direct, and a healthy configured worker parent still does its own routine " +
        "work. This routing belongs to the parent; delegated workers never re-delegate.");
  }
  if (config.preset === "antigravity") {
    parts.push(
      `Antigravity execution: the configured worker executor is ${config.workerExecutor ?? "antigravity_delegate"}. ` +
        "For every eligible bounded Git implementation task, it is mandatory to call " +
        "`antigravity_delegate` as the primary worker in an existing clean linked Git " +
        "worktree; the parent must not implement that task directly. Inspect its returned " +
        "diff and focused test evidence before delivery. Keep trivial or read-only work " +
        "direct, and if no eligible linked worktree exists, report that blocker rather " +
        "than silently bypassing the Agy worker.");
  }
  const eligible = ROLE_KEYS.filter((key) => ELIGIBLE.has(key) && identity(config.roles[key]) === DEEPSEEK_FLASH);
  if (eligible.length > 0) {
    const perRole = eligible.map((key) => `${key} ${config.roles[key].thinking}`).join(", ");
    parts.push(
      `Fallback for ${eligible.join("/")} whose configured primary is ${DEEPSEEK_FLASH}, ` +
        `only after an actual provider or model-specific failure: keep the role's configured ` +
        `thinking level (${perRole}), then ${FALLBACK}, at most ` +
        "two transitions. Confirm the old writer has stopped before replacing it; " +
        "carry the existing diff, evidence and verification; no speculative standby " +
        "agents and no retry loop. Auth/permission failures, shared outages and " +
        "uncertain writes need reconciliation, not model hopping; never buy credits. A " +
        "confirmed provider-specific insufficient balance or unavailability permits " +
        "the next user-approved provider.");
  }
  return `\n\n${parts.join("\n\n")}\n`;
}

export default function roleRouting(pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event) => {
    const agentDir = process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent");
    const read = readConfig(join(agentDir, "megai-roles.json"));
    if (read.kind === "missing") return;
    const config = read.kind === "data" ? parseConfig(read.text) : undefined;
    return { systemPrompt: event.systemPrompt + (config ? render(config) : BLOCKED) };
  });
}
