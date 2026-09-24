/** megai-laya-current-0.3.20: only exact duplicate text is expendable.
 * Any unsupported message or unique result returns control to Pi's native summarizer.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm } from "@earendil-works/pi-coding-agent";

type Decide = (state: string, questions: Record<string, unknown>, signal?: AbortSignal) => Promise<any>;

export function registerCompaction(pi: ExtensionAPI, decide: Decide): void {
  pi.on("session_before_compact", async (event) => {
    try {
      const { preparation, reason, customInstructions, signal } = event;
      if (reason === "overflow" || customInstructions?.trim()) return;
      const messages = convertToLlm([
        ...preparation.messagesToSummarize, ...preparation.turnPrefixMessages,
      ]);
      const lines: Array<{ text: string; duplicate?: boolean; meta?: string }> = [];
      const seen = new Set<string>();
      let originalChars = 0;
      let duplicateCount = 0;
      for (const message of messages) {
        if (message.role !== "user" && message.role !== "assistant" && message.role !== "toolResult") return;
        const content = message.content;
        if (typeof content !== "string" && !Array.isArray(content)) return;
        const pieces: string[] = [];
        for (const item of Array.isArray(content) ? content : [{ type: "text", text: content }]) {
          if (item?.type === "text" && typeof item.text === "string") pieces.push(item.text);
          else if (message.role === "assistant" && item?.type === "toolCall")
            pieces.push(`[Assistant tool calls]: ${item.name}(${JSON.stringify(item.arguments ?? {})})`);
          else return; // images, redacted payloads or unknown blocks cannot be reproduced.
        }
        const text = pieces.join("\n");
        if (!text) continue;
        originalChars += text.length;
        // Text alone is not enough identity: an error and a successful result,
        // or two different tools, may legitimately emit the same bytes.
        const meta = message.role === "toolResult"
          ? ` tool=${message.toolName ?? "unknown"} call=${message.toolCallId ?? "unknown"} error=${Boolean(message.isError)}`
          : "";
        const identity = message.role === "toolResult"
          ? JSON.stringify([message.toolName ?? "", Boolean(message.isError), text])
          : "";
        const duplicate = message.role === "toolResult" && seen.has(identity) && text.length >= 500;
        if (message.role === "toolResult") seen.add(identity);
        if (duplicate) duplicateCount++;
        lines.push({ text: `[${message.role}${meta}]: ${text}`, duplicate, meta });
      }
      if (!duplicateCount || !originalChars || originalChars > 20_000) return;
      const answers = await decide(
        `The complete span has ${lines.length} supported text entries. ${duplicateCount} tool results are byte-identical to earlier results retained verbatim. No unique result will be deleted.`,
        { redundant: { type: "noul", instructions: "Removing identical repeated outputs while retaining their earlier exact copy is safe for the user's task." } },
        signal,
      );
      const safety = answers.answers?.redundant?.noul;
      if (typeof safety !== "number" || !Number.isFinite(safety) || safety <= 0.5) return;
      const summary = [preparation.previousSummary || "", "Compacted transcript (only byte-identical repeated tool outputs omitted):",
        ...lines.map(line => line.duplicate
          ? `[Tool result${line.meta ?? ""}]: repeated exact text retained earlier.`
          : line.text)]
        .filter(Boolean).join("\n\n");
      if (summary.length > 8_192 || summary.length >= originalChars * 0.85) return;
      const modified = new Set<string>([...(preparation.fileOps?.written ?? []), ...(preparation.fileOps?.edited ?? [])]);
      return {
        compaction: {
          summary,
          firstKeptEntryId: preparation.firstKeptEntryId,
          tokensBefore: preparation.tokensBefore,
          details: {
            readFiles: [...(preparation.fileOps?.read ?? [])].filter(file => !modified.has(file)).sort(),
            modifiedFiles: [...modified].sort(),
            laya: { duplicateResultsOmitted: duplicateCount, uniqueResultsOmitted: 0 },
          },
        },
      };
    } catch {
      return; // Pi's own native summarizer sees the full original span.
    }
  });
}
