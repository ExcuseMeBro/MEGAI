import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/** Bound provider waits, not task duration. Never interrupt an executing tool. */
export default function providerGuard(pi: ExtensionAPI) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let active = false;
  let timeoutMs = 180_000;
  let startedAt = 0;
  const tools = new Set<string>();
  const clear = () => {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  };
  const reset = () => { clear(); active = false; tools.clear(); };

  pi.on("session_start", (_event, ctx) => {
    reset();
    const raw = process.env.MEGAI_PROVIDER_TIMEOUT_MS;
    const value = raw === undefined ? 180_000 : Number(raw);
    // Explicit 0 opts out. Reject invalid values without silently disabling safety.
    timeoutMs = Number.isSafeInteger(value) && value >= 0 && value <= 2_147_483_647
      && (raw === undefined || /^\d+$/.test(raw)) ? value : 180_000;
    if (raw !== undefined && String(timeoutMs) !== raw && ctx.hasUI) {
      ctx.ui.notify("MEGAI: invalid provider timeout; using 180000ms", "warning");
    }
  });
  pi.on("agent_start", () => { active = true; });
  pi.on("before_provider_request", (_event, ctx) => {
    // Nested provider work inside tools belongs to the tool's own cancellation
    // contract. Retry agent_start events must not reset an existing deadline.
    if (!active || tools.size || timer !== undefined || timeoutMs === 0) return;
    startedAt = Date.now();
    timer = setTimeout(() => {
      timer = undefined;
      try {
        if (!active || tools.size || ctx.isIdle()) return;
        // Abort first: reporting failures must not prevent cancellation. Pi marks
        // this assistant response aborted (not retryable) and keeps prior results.
        ctx.abort();
      } catch {
        // Direct SDK disposal can invalidate ctx without session_shutdown;
        // disposal already aborts the agent. Never crash on a stale callback.
        return;
      }
      const elapsedMs = Date.now() - startedAt;
      try {
        pi.appendEntry("megai-provider-timeout", { timeoutMs, elapsedMs });
      } catch {
        console.error("MEGAI: provider wait aborted; timeout diagnostic could not be saved.");
      }
      try {
        if (ctx.hasUI) ctx.ui.notify(
          `MEGAI: provider wait exceeded ${timeoutMs}ms; aborted without replaying tools. Resume from saved evidence or escalate; do not blame the last tool.`,
          "error",
        );
      } catch {
        console.error("MEGAI: provider wait aborted; timeout notification unavailable.");
      }
    }, timeoutMs);
    timer.unref();
  });
  pi.on("message_end", event => {
    // Keep the same budget during native automatic retries and their backoff.
    if (event.message.role === "assistant" && event.message.stopReason !== "error") clear();
  });
  pi.on("tool_execution_start", event => { tools.add(event.toolCallId); clear(); });
  pi.on("tool_execution_end", event => { tools.delete(event.toolCallId); });
  pi.on("agent_settled", reset);
  pi.on("session_compact", clear);
  pi.on("session_compact_failed", clear);
  pi.on("session_shutdown", reset);
}
