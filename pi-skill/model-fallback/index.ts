/**
 * MEGAI provider fallback.
 *
 * A settled run that ended on a provider-level failure continues in the same
 * session on the configured partner model, so one provider's outage or exhausted
 * balance stops the task instead of the session. The failed model is remembered
 * for the session: a partner that also fails is never swapped back to the first,
 * so failures cannot ping-pong between providers.
 *
 * Authorization/permission and context-overflow errors never trigger a swap: those
 * need reconciliation or compaction, not a different provider. Provider-specific
 * exhaustion is deliberately *not* on that list — an exhausted balance or plan limit
 * is exactly what the partner provider is for. The pair comes
 * from `model-fallback.json` in the Pi agent directory when that file is readable
 * and valid, otherwise from `DEFAULT_FALLBACKS`; an empty `fallbacks` object
 * disables the swap. Nothing else changes: no role, credential, tool or
 * thinking-level edit, and the user always sees a notification and a session entry.
 *
 * The continuation is queued as a follow-up while the run is still alive, because a
 * prompt sent after the run settles is dropped in headless (`--print`) sessions.
 */
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const DEFAULT_FALLBACKS: Record<string, string> = {
  "deepseek/deepseek-flash": "openai-codex/gpt-5.6-sol",
  "openai-codex/gpt-5.6-sol": "deepseek/deepseek-flash",
};
const MAX_CONFIG_BYTES = 32 * 1024;
const MAX_PAIRS = 16;
const IDENTITY = /^[A-Za-z0-9._:-]{1,64}\/[A-Za-z0-9._:\/-]{1,96}$/;
/**
 *
 * Failures another provider cannot fix: authorization, permission and a quota the
 * providers share need reconciliation, and a context overflow needs compaction.
 * `invalid_request` is deliberately absent — DeepSeek reports its 402 balance error
 * under that code — and so are 429, plan limits and balance errors: those are
 * provider-specific exhaustion, which the partner exists to cover.
 */
const NOT_PROVIDER =
  /\b(401|403)\b|unauthorized|forbidden|permission denied|api[- ]?key|authentication|shared.{0,16}(quota|outage|limit)|context[_ ]|\bcontext\b.{0,32}(length|window|overflow|size|limit)|prompt (?:is )?too long|too long for requested model|request_too_large|maximum prompt length|reduce the length of the messages|exceeds (?:the )?(?:maximum|limit)|too large for model|too many tokens|token limit|range of input length/i;
const CONTINUE =
  "The previous provider request failed before this task finished. Continue the unfinished work " +
  "from the existing context, diff and evidence, and verify what actually completed instead of " +
  "repeating commands that already ran.";

type Failure = { from: string; reason: string };

let pending: Failure | undefined;
const failed = new Set<string>();

/** Bounded read of the optional user override; anything unusable keeps the defaults. */
function readFallbacks(): Record<string, string> {
  const agentDir = process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent");
  try {
    const path = join(agentDir, "model-fallback.json");
    if (statSync(path).size > MAX_CONFIG_BYTES) return DEFAULT_FALLBACKS;
    const parsed: unknown = JSON.parse(readFileSync(path, "utf8"));
    const map = parsed !== null && typeof parsed === "object"
      ? (parsed as { fallbacks?: unknown }).fallbacks : undefined;
    if (map === null || typeof map !== "object" || Array.isArray(map)) return DEFAULT_FALLBACKS;
    const entries = Object.entries(map as Record<string, unknown>);
    if (entries.length > MAX_PAIRS) return DEFAULT_FALLBACKS;
    const pairs: Record<string, string> = {};
    for (const [from, to] of entries) {
      if (!IDENTITY.test(from) || typeof to !== "string" || !IDENTITY.test(to)) return DEFAULT_FALLBACKS;
      pairs[from] = to;
    }
    return pairs;
  } catch {
    return DEFAULT_FALLBACKS;
  }
}

function summarize(message: string): string {
  return message.replace(/\s+/g, " ").trim().slice(0, 200) || "provider error";
}

export default function modelFallback(pi: ExtensionAPI) {
  pi.on("session_start", () => {
    pending = undefined;
    failed.clear();
  });

  // Only this event carries the authoritative error text; the run may still retry.
  pi.on("message_end", (event) => {
    if (event.message.role !== "assistant") return;
    const message = event.message;
    pending = message.stopReason === "error"
      ? { from: `${message.provider}/${message.model}`, reason: summarize(message.errorMessage ?? "") }
      : undefined;
  });

  // The run is still alive here, so the continuation must be queued as a follow-up.
  // After agent_settled a headless session is already finishing and drops the prompt.
  pi.on("agent_end", async (_event, ctx: ExtensionContext) => {
    const failure = pending;
    pending = undefined;
    if (!failure) return;
    failed.add(failure.from);
    if (NOT_PROVIDER.test(failure.reason)) return;
    const partner = readFallbacks()[failure.from];
    if (!partner || failed.has(partner)) return;
    const slash = partner.indexOf("/");
    const target = ctx.modelRegistry.find(partner.slice(0, slash), partner.slice(slash + 1));
    if (!target || !(await pi.setModel(target))) return;
    pi.appendEntry("megai-model-fallback", { from: failure.from, to: partner, reason: failure.reason });
    if (ctx.hasUI) {
      ctx.ui.notify(`MEGAI: ${failure.from} failed (${failure.reason}); continuing on ${partner}.`, "warning");
    }
    pi.sendUserMessage(`${CONTINUE}\n\nFailed provider: ${failure.from} — ${failure.reason}`,
      { deliverAs: "followUp" });
  });
}
