/**
 * Laya fast compaction on the local Laya runtime.
 *
 * Pi normally spends one LLM summarization call on the span it discards. This
 * replaces that with two cheap `noul` questions per tool call in the span: keep
 * the call, keep its result. The assistant and user text, every tool call, and
 * every result Laya scores as still needed stay verbatim; a result judged stale
 * collapses to a one-line note, and a stale call disappears together with its
 * result. The summary is a transcript with holes cut out, not a paraphrase —
 * orders of magnitude cheaper and faster than a summarization call, and nothing
 * that mattered is reworded.
 *
 * It can never block a compaction. Without a local runtime, with
 * `/compact <instructions>` (a focused summary we cannot honor), on overflow
 * recovery (which needs a summary guaranteed to be small), when the span has no
 * tool calls, or when Laya drops nothing, the handler returns `undefined` and Pi's
 * own summarization runs exactly as before. A failed or unreadable Laya batch keeps
 * everything it asked about.
 *
 * The active Laya extension registers this handler with its own `layaPost` function,
 * so compaction cannot create or own a second model process even when Pi/Jiti disables
 * its module cache.
 *
 * Deviations from the Claude Code plugin: thinking blocks are dropped rather than
 * judged, a kept result is capped at `MAX_RESULT_CHARS` so a compaction always
 * frees space, and the previous summary is carried forward verbatim because Pi
 * discards it after each cycle.
 * ponytail: the carried summary grows by one span per cycle. If a very long
 * session's chain ever gets too big, fold older cycles into one Laya-kept pass.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm } from "@earendil-works/pi-coding-agent";

type LayaPost = (
  state: string,
  questions: Record<string, unknown>,
  lang: string | undefined,
  signal?: AbortSignal,
  source?: string,
) => Promise<{ ok: true; answers: Record<string, unknown> } | { ok: false; error: string }>;

/** `noul` probability at or above which a call or result is kept. */
const KEEP_THRESHOLD = 0.5;
/** The bridge accepts eight questions and each call asks two. */
const CALLS_PER_REQUEST = 4;
/** Verbatim budget per kept result; the rest is noted, never silently lost. */
const MAX_RESULT_CHARS = 4_000;
const MAX_ARGS_CHARS = 200;
const MAX_GOAL_CHARS = 1_500;
const GOAL_MESSAGES = 3;

const HEADER = "Compacted transcript of earlier turns (Laya fast compaction: kept verbatim, " +
  "entries marked `dropped` were judged stale — re-run the tool if they matter now).";

interface ToolCall {
  seq: number;
  name: string;
  args: string;
  resultChars: number;
}

interface Block {
  kind: "text" | "call" | "result";
  text: string;
  call?: ToolCall;
}

/** `keep` keeps call and result, `drop_result` keeps the call with a note, and
 * `drop_call` removes both — the same three outcomes as the original plugin. */
type Action = "keep" | "drop_result" | "drop_call";

function clip(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max)}…`;
}

function textOf(content: unknown): string {
  if (typeof content === "string") return content.trim();
  if (!Array.isArray(content)) return "";
  return content
    .filter((part: any) => part?.type === "text" && typeof part.text === "string")
    .map((part: any) => part.text)
    .join("\n")
    .trim();
}

/** The discarded span as ordered blocks, with every tool call numbered so the
 * questions can name it. Thinking blocks are dropped: the assistant already acted
 * on that reasoning, and it is the cheapest space in the span to give back. */
function blocksOf(messages: readonly any[]): { blocks: Block[]; calls: ToolCall[]; chars: number } {
  const blocks: Block[] = [];
  const calls: ToolCall[] = [];
  const byId = new Map<string, ToolCall>();
  let chars = 0;
  for (const message of messages ?? []) {
    if (message?.role === "user") {
      const text = textOf(message.content);
      if (text) {
        blocks.push({ kind: "text", text: `[User]: ${text}` });
        chars += text.length;
      }
      continue;
    }
    if (message?.role === "assistant") {
      const text = textOf(message.content);
      if (text) {
        blocks.push({ kind: "text", text: `[Assistant]: ${text}` });
        chars += text.length;
      }
      for (const part of Array.isArray(message.content) ? message.content : []) {
        if (part?.type !== "toolCall") continue;
        const call: ToolCall = {
          seq: calls.length + 1,
          name: typeof part.name === "string" && part.name ? part.name : "tool",
          args: clip(JSON.stringify(part.arguments ?? {}), MAX_ARGS_CHARS),
          resultChars: 0,
        };
        calls.push(call);
        if (typeof part.id === "string") byId.set(part.id, call);
        blocks.push({ kind: "call", text: "", call });
        chars += call.args.length;
      }
      continue;
    }
    if (message?.role === "toolResult") {
      const text = textOf(message.content);
      const call = typeof message.toolCallId === "string" ? byId.get(message.toolCallId) : undefined;
      if (call) call.resultChars = text.length;
      blocks.push({ kind: "result", text, call });
      chars += text.length;
    }
  }
  return { blocks, calls, chars };
}

/** What the session is working on, from the newest user messages in the span. */
function goalOf(messages: readonly any[]): string {
  const said = (messages ?? [])
    .filter((message) => message?.role === "user")
    .map((message) => textOf(message.content))
    .filter(Boolean)
    .slice(-GOAL_MESSAGES);
  return clip(said.join("\n"), MAX_GOAL_CHARS);
}

/** The state every batch is answered from: the goal, what came before, and the
 * numbered calls whose fate is being decided. Results stay out — their size, not
 * their text, is what the question turns on. */
function stateFor(goal: string, calls: readonly ToolCall[], carried: string): string {
  return [
    carried.trim() && `Earlier compaction summary:\n${carried.trim()}`,
    goal && `What the session is working on:\n${goal}`,
    `Tool calls inside the span being compressed, in order:\n` +
      calls.map((call) => `${call.seq}. ${call.name}(${call.args}) — result ${call.resultChars} chars`).join("\n"),
  ]
    .filter(Boolean)
    .join("\n\n");
}

function questionsFor(call: ToolCall): Record<string, unknown> {
  return {
    [`call_${call.seq}`]: {
      type: "noul",
      instructions: `Tool call ${call.seq} (${call.name}) should stay in the history: knowing that this ` +
        `exact call was made, with its input, still matters for what the assistant does next.`,
    },
    [`result_${call.seq}`]: {
      type: "noul",
      instructions: `The output of tool call ${call.seq} (${call.name}, ${call.resultChars} chars) should stay ` +
        `in the history verbatim: the assistant still needs its contents and re-running the tool would not do.`,
    },
  };
}

/** The `noul` probability of one answer, or `undefined` when it is not a number. */
function noul(answer: unknown): number | undefined {
  const value = (answer as any)?.noul ?? answer;
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

/**
 * Two questions per call, `MAX_QUESTIONS` per request, requests in parallel. A
 * batch that fails or answers unusably keeps everything it asked about: a
 * compaction that frees less context beats one that silently loses a result.
 */
async function decide(
  calls: readonly ToolCall[],
  state: string,
  signal: AbortSignal,
  layaPost: LayaPost,
): Promise<{ decisions: Map<number, Action>; requests: number; failed: number }> {
  const batches: ToolCall[][] = [];
  for (let index = 0; index < calls.length; index += CALLS_PER_REQUEST) {
    batches.push(calls.slice(index, index + CALLS_PER_REQUEST));
  }
  const answers = await Promise.all(
    batches.map(async (batch) => ({
      batch,
      result: await layaPost(state, Object.assign({}, ...batch.map(questionsFor)), undefined, signal, "compaction"),
    })),
  );
  const decisions = new Map<number, Action>();
  let failed = 0;
  for (const { batch, result } of answers) {
    if (!result.ok) {
      failed += 1;
      for (const call of batch) decisions.set(call.seq, "keep");
      continue;
    }
    for (const call of batch) {
      const kept = result.answers as Record<string, unknown>;
      const keepCall = noul(kept[`call_${call.seq}`]);
      const keepResult = noul(kept[`result_${call.seq}`]);
      // A wanted result implies its call stays: a result without the call that
      // produced it is unreadable.
      decisions.set(
        call.seq,
        keepCall === undefined || keepResult === undefined || keepResult >= KEEP_THRESHOLD
          ? "keep"
          : keepCall >= KEEP_THRESHOLD
            ? "drop_result"
            : "drop_call",
      );
    }
  }
  return { decisions, requests: batches.length, failed };
}

function render(
  blocks: readonly Block[],
  decisions: ReadonlyMap<number, Action>,
  carried: string,
): string {
  const parts: string[] = [HEADER];
  if (carried.trim()) parts.push(carried.trim());
  for (const block of blocks) {
    if (block.kind === "text") {
      parts.push(block.text);
      continue;
    }
    const action = block.call ? decisions.get(block.call.seq) : undefined;
    if (block.kind === "call") {
      if (action === "drop_call") continue;
      parts.push(`[Assistant tool calls]: ${block.call!.name}(${block.call!.args})`);
      continue;
    }
    if (action === "drop_call") continue;
    if (action === "drop_result" && block.call) {
      parts.push(`[Tool result]: ${block.call.name} — dropped as stale (${block.call.resultChars} chars).`);
      continue;
    }
    const name = block.call ? `${block.call.name}: ` : "";
    const text = block.text.length <= MAX_RESULT_CHARS
      ? block.text
      : `${block.text.slice(0, MAX_RESULT_CHARS)}\n[${block.text.length - MAX_RESULT_CHARS} chars not kept; re-run the tool if they matter]`;
    parts.push(`[Tool result]: ${name}${text}`);
  }
  return parts.join("\n\n");
}

/** Read-only and modified files of the span, in the shape Pi's default compaction
 * records — the only trace of a call the transcript itself no longer mentions. */
function fileLists(fileOps: any): { readFiles: string[]; modifiedFiles: string[] } {
  const modified = new Set<string>([...(fileOps?.written ?? []), ...(fileOps?.edited ?? [])]);
  return {
    readFiles: [...(fileOps?.read ?? [])].filter((file: string) => !modified.has(file)).sort(),
    modifiedFiles: [...modified].sort(),
  };
}

export function registerLayaCompaction(pi: ExtensionAPI, layaPost: LayaPost) {
  pi.on("session_before_compact", async (event, ctx) => {
    try {
      const { preparation, reason, customInstructions, signal } = event;
      // A focused `/compact <instructions>` wants a summary this cannot produce,
      // and overflow recovery needs a summary guaranteed to be small.
      if (reason === "overflow" || customInstructions?.trim()) return;

      const messages = [...preparation.messagesToSummarize, ...preparation.turnPrefixMessages];
      const { blocks, calls, chars } = blocksOf(convertToLlm(messages));
      if (calls.length === 0) return;

      const carried = preparation.previousSummary ?? "";
      const started = Date.now();
      const { decisions, requests, failed } = await decide(
        calls,
        stateFor(goalOf(messages), calls, carried),
        signal,
        layaPost,
      );
      const resultsDropped = calls.filter((call) => decisions.get(call.seq) === "drop_result").length;
      const callsDropped = calls.filter((call) => decisions.get(call.seq) === "drop_call").length;
      // Nothing stale to cut, so the transcript would only be as long as the span
      // it replaces: let Pi's own summary do the shrinking.
      if (resultsDropped + callsDropped === 0) return;

      const summary = render(blocks, decisions, carried);
      const files = fileLists(preparation.fileOps);
      ctx.ui.notify(
        `Laya compaction: ${calls.length} calls, ${resultsDropped} results and ${callsDropped} calls dropped, ` +
          `${chars} → ${summary.length} chars, ${requests} local calls in ${Date.now() - started} ms` +
          (failed ? ` (${failed} batches kept everything)` : ""),
        failed ? "warning" : "info",
      );
      return {
        compaction: {
          summary,
          firstKeptEntryId: preparation.firstKeptEntryId,
          tokensBefore: preparation.tokensBefore,
          details: {
            ...files,
            laya: {
              calls: calls.length,
              kept: calls.filter((call) => decisions.get(call.seq) === "keep").length,
              resultsDropped,
              callsDropped,
              requests,
              failed,
              charsBefore: chars,
              charsAfter: summary.length,
              ms: Date.now() - started,
            },
          },
        },
      };
    } catch (error) {
      ctx.ui.notify(`Laya compaction failed (${error instanceof Error ? error.message : String(error)}); using Pi's summary`, "warning");
      return;
    }
  });
}
