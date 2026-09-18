/**
 * TypeSafe System One ("Jev") decision tool.
 *
 * One bounded POST per call for typed decision questions (`choice`, `score`,
 * `noul`). The key comes from `TYPESAFE_API_KEY`, the macOS keychain, or — when
 * neither has one and a dialog is available — a single user prompt whose answer is
 * kept in memory for the session; it is never logged, returned, or written into
 * tool output. Every failure returns `ok: false` with a one-line reason, so the
 * agent falls back to its own judgment instead of retrying, blocking, or guessing
 * about the service. `TYPESAFE_ENDPOINT` overrides the public endpoint and
 * `TYPESAFE_TIMEOUT_MS` the 30 s deadline, for a proxy or an offline test.
 *
 * The same key and `jevPost` drive the tool-call gate below: every tool call the
 * model emits — built-in, `mcp`, `mcpScript`, all of them — gets one `noul`
 * judgment before it runs. Advisory by default, `JEV_GATE_BLOCK=1` to block,
 * `JEV_GATE=0` to switch the gate off, and always fail open.
 */
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execFileSync } from "node:child_process";
import { platform } from "node:os";

const DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone";
const MODEL = "jev-latest";
const SERVICE = "typesafe.ai";
const TIMEOUT_MS = Math.max(0, Number(process.env.TYPESAFE_TIMEOUT_MS)) || 30_000;
const DIALOG_MS = 120_000;
const MAX_STATE = 24_000;
const MAX_BODY = 256 * 1024;
export const MAX_QUESTIONS = 8;
const MAX_CRITERIA = 12;
const KINDS = ["choice", "score", "noul"];
/** `noul` probability at or above which a judged tool call runs unquestioned. */
const GATE_THRESHOLD = 0.5;
const GATE_TIMEOUT_MS = Math.max(0, Number(process.env.JEV_GATE_TIMEOUT_MS)) || 5_000;
const GATE_ARGS_CHARS = 800;
const GATE_GOAL_CHARS = 1_200;
/** The gate never judges itself: a Jev question about the `jev` call would recurse. */
const GATE_SKIP = new Set(["jev"]);

let cachedKey: string | undefined;

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function clip(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max)}…`;
}

/** The goal every gate judgment is made against: the newest user message on the
 * live branch, or nothing when the caller has no session to read. */
function goalOf(ctx: ExtensionContext): string {
  let entries: any[];
  try {
    entries = [...ctx.sessionManager.getBranch()];
  } catch {
    return "";
  }
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    const message: any = entries[index]?.message;
    if (entries[index]?.type !== "message" || message?.role !== "user") continue;
    const content = message.content;
    const text = typeof content === "string" ? content : Array.isArray(content)
      ? content.filter((part: any) => part?.type === "text" && typeof part.text === "string")
        .map((part: any) => part.text).join("\n")
      : "";
    if (text.trim()) return clip(text.trim(), GATE_GOAL_CHARS);
  }
  return "";
}

/** The `noul` probability of one answer, or `undefined` when it is not a number. */
function probability(answer: unknown): number | undefined {
  const value = (answer as any)?.noul ?? answer;
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

/** The gate's deadline, whichever comes first: the agent's own abort or its own. */
function gated(ctx: ExtensionContext): AbortSignal {
  const deadline = AbortSignal.timeout(GATE_TIMEOUT_MS);
  return ctx.signal ? AbortSignal.any([ctx.signal, deadline]) : deadline;
}

function keychainKey(): string | undefined {
  if (platform() !== "darwin") return undefined;
  try {
    const value = execFileSync("security", ["find-generic-password", "-s", SERVICE, "-w"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], timeout: 5_000 }).trim();
    return value || undefined;
  } catch {
    return undefined;
  }
}

/** Environment first, then the macOS keychain. A miss is remembered too (as
 * `""`), so a keychain-less macOS session spawns `security` at most once. */
export function apiKey(): string | undefined {
  const provided = process.env.TYPESAFE_API_KEY?.trim();
  if (provided) return provided;
  if (cachedKey === undefined) cachedKey = keychainKey() ?? "";
  return cachedKey || undefined;
}

/** Ask the user once per session for a missing key and keep the answer in memory.
 * The dialog is plain text, so the keychain or the environment stays the durable
 * route; a headless child, a closed dialog, or a cancel simply means no key. */
async function askForKey(ctx: ExtensionContext | undefined): Promise<string | undefined> {
  if (!ctx?.hasUI) return undefined;
  try {
    const entered = (await ctx.ui.input(
      "TypeSafe API key for this session (store it with `security add-generic-password -s typesafe.ai -a \"$USER\" -w` to keep it)",
      "paste the key",
      { timeout: DIALOG_MS },
    ))?.trim();
    if (!entered) return undefined;
    cachedKey = entered;
    return entered;
  } catch {
    return undefined;
  }
}

function criteria(value: unknown, id: string): string[] | Record<string, string | null> {
  if (Array.isArray(value)) {
    if (value.length === 0 || value.length > MAX_CRITERIA) throw new Error(`invalid criteria for "${id}"`);
    return value.map((item) => {
      if (typeof item !== "string" || !item.trim()) throw new Error(`invalid criteria for "${id}"`);
      return item.trim();
    });
  }
  if (!value || typeof value !== "object") throw new Error(`invalid criteria for "${id}"`);
  const entries = Object.entries(value as Record<string, unknown>);
  if (entries.length === 0 || entries.length > MAX_CRITERIA) throw new Error(`invalid criteria for "${id}"`);
  const shaped: Record<string, string | null> = {};
  for (const [name, text] of entries) {
    if (!name.trim() || (text !== null && (typeof text !== "string" || !text.trim())))
      throw new Error(`invalid criteria for "${id}"`);
    shaped[name.trim()] = text === null ? null : (text as string).trim();
  }
  return shaped;
}

/** The live API takes an ordered level list for `score` and a label→meaning map
 * for `choice`/`noul`. Its other accepted shape is converted here, never forwarded
 * blind: a wrong shape comes back as HTTP 422, which used to make every `choice`
 * call with a plain label list fail. */
function shapedCriteria(type: string, value: unknown, id: string): string[] | Record<string, string | null> {
  const parsed = criteria(value, id);
  if (type === "score") return Array.isArray(parsed) ? parsed : Object.keys(parsed);
  return Array.isArray(parsed) ? Object.fromEntries(parsed.map((label) => [label, null])) : parsed;
}

/** Validate the caller's questions; a malformed question never reaches the network. */
function questionPayload(questions: Record<string, unknown>): Record<string, unknown> {
  const entries = Object.entries(questions ?? {});
  if (entries.length === 0 || entries.length > MAX_QUESTIONS)
    throw new Error(`1-${MAX_QUESTIONS} questions required`);
  const payload: Record<string, unknown> = {};
  for (const [id, raw] of entries) {
    if (!/^[A-Za-z][A-Za-z0-9_]{0,31}$/.test(id)) throw new Error(`invalid question id "${id}"`);
    const question = (raw ?? {}) as Record<string, unknown>;
    if (!KINDS.includes(question.type as string)) throw new Error(`invalid question type for "${id}"`);
    const instructions = typeof question.instructions === "string" ? question.instructions.trim() : "";
    if (!instructions || instructions.length > 2_000) throw new Error(`invalid instructions for "${id}"`);
    if (question.criteria === undefined) {
      if (question.type === "choice" || question.type === "score")
        throw new Error(`criteria required for "${id}" (${question.type})`);
      payload[id] = { type: question.type, instructions };
    } else {
      payload[id] = {
        type: question.type,
        instructions,
        criteria: shapedCriteria(question.type as string, question.criteria, id),
      };
    }
  }
  return payload;
}

function failed(reason: string) {
  return {
    content: [{
      type: "text" as const,
      text: JSON.stringify({
        ok: false,
        error: reason,
        guidance: "Decide with your own judgment, record that the Jev call failed, and continue; do not retry in a loop.",
      }),
    }],
    details: {},
  };
}

/** One Jev POST, shared by the `jev` tool and any companion extension. Validation
 * stays with the caller; a network or protocol failure comes back as `ok: false`
 * with a one-line reason instead of throwing, so a caller falls back on its own. */
export async function jevPost(
  key: string,
  state: string,
  questions: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<
  | { ok: true; answers: Record<string, unknown>; model: string; usage: unknown }
  | { ok: false; error: string }
> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch(process.env.TYPESAFE_ENDPOINT || DEFAULT_ENDPOINT, {
      method: "POST",
      headers: { authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: JSON.stringify({ state, model: MODEL, questions }),
      signal: controller.signal,
    });
    if (!response.ok) return { ok: false, error: `Jev returned HTTP ${response.status}` };
    const text = await response.text();
    if (text.length > MAX_BODY) return { ok: false, error: "Jev response too large" };
    let payload: any;
    try {
      payload = JSON.parse(text);
    } catch {
      return { ok: false, error: "Jev response was not JSON" };
    }
    if (!payload?.answers || typeof payload.answers !== "object") {
      return { ok: false, error: "Jev response carried no answers" };
    }
    return { ok: true, answers: payload.answers, model: payload.model ?? MODEL, usage: payload.usage ?? null };
  } catch (error: any) {
    const kind = [error?.name, error?.code].filter(Boolean).join(" ") || "unknown";
    return {
      ok: false,
      error: controller.signal.aborted
        ? "Jev call timed out or was cancelled"
        : `Jev call failed (${kind})`,
    };
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

export default function jev(pi: ExtensionAPI) {
  pi.registerTool({
    name: "jev",
    label: "TypeSafe decision",
    description: "TypeSafe System One typed decision call: 1-8 `choice`, `score` or `noul` " +
      "questions about supplied state, answered in about a second with probabilities. Use it " +
      "for every workflow step decision — triage mode/type/effort/approval, Plane labels, " +
      "isolation, delegation and role, verification depth, verdict, delivery readiness and " +
      "handoff — one call per decision boundary with that step's independent questions " +
      "bundled, instead of asking a model. Send only the request " +
      "text needed for the decision: no secrets, credentials or personal data. Answers are " +
      "advisory, never authorize a reserved user decision, and belong on the task item. " +
      "On ok:false, decide yourself.",
    parameters: Type.Object({
      state: Type.String({
        minLength: 1, maxLength: MAX_STATE,
        description: "The text the questions are answered from: the request, the policy, or the diff summary. No secrets or personal data.",
      }),
      questions: Type.Record(Type.String(), Type.Object({
        type: Type.Union([Type.Literal("choice"), Type.Literal("score"), Type.Literal("noul")]),
        instructions: Type.String({ minLength: 1, maxLength: 2_000 }),
        criteria: Type.Optional(Type.Union([
          Type.Array(Type.String({ maxLength: 200 }), { maxItems: MAX_CRITERIA }),
          Type.Record(Type.String(), Type.Union([Type.String({ maxLength: 200 }), Type.Null()])),
        ], { description: "choice/noul: label→meaning map (a bare label list is accepted too); score: ordered level list" })),
      }), {
        description: "Questions and criteria are sent to the API with `state`: no secrets, credentials or personal data",
      }),
    }),
    async execute(_id, params, signal, _onUpdate, ctx) {
      let questions: Record<string, unknown>;
      try {
        questions = questionPayload(params.questions);
      } catch (error) {
        return failed(message(error));
      }
      const key = apiKey() ?? await askForKey(ctx);
      if (!key) {
        return failed("no TypeSafe key: enter one when asked, set TYPESAFE_API_KEY, or store one with " +
          "`security add-generic-password -s typesafe.ai -a \"$USER\" -w`");
      }
      const result = await jevPost(key, params.state, questions, signal);
      if (!result.ok) return failed(result.error);
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify({ ok: true, model: result.model, answers: result.answers, usage: result.usage }),
        }],
        details: {},
      };
    },
  });

  /** The gate: one Jev `noul` judgment per tool call the model emits, before the
   * tool runs. Advisory by default — a doubtful call is reported and still runs —
   * and every failure (no key, timeout, error, no session) lets the call through
   * rather than inventing a verdict. `JEV_GATE_BLOCK=1` blocks the call and tells
   * the model why; `JEV_GATE=0` turns the gate off for a session. */
  pi.on("tool_call", async (event, ctx) => {
    if (process.env.JEV_GATE === "0" || GATE_SKIP.has(event.toolName)) return;
    const key = apiKey();
    if (!key) return;

    const goal = goalOf(ctx);
    const state = [
      "Judge whether the next tool call from the model should run exactly as it is.",
      goal && `What the session is working on:\n${goal}`,
      `Working directory: ${ctx.cwd}`,
      `Tool call: ${event.toolName}(${clip(JSON.stringify(event.input ?? {}), GATE_ARGS_CHARS)})`,
    ].filter(Boolean).join("\n\n");

    const result = await jevPost(key, state, {
      should_run: {
        type: "noul",
        instructions: `This exact ${event.toolName} call is the right next step for what the session ` +
          `is working on and should run unchanged, rather than a different, narrower or no call.`,
      },
    }, gated(ctx));
    if (!result.ok) return;

    const confidence = probability((result.answers as Record<string, unknown>)?.should_run);
    if (confidence === undefined || confidence >= GATE_THRESHOLD) return;

    const reason = `Jev gate: this ${event.toolName} call is questionable for the current goal ` +
      `(should_run ${confidence}). Re-check it against the request, narrow it, or say why it is needed.`;
    if (process.env.JEV_GATE_BLOCK === "1") return { block: true, reason };
    ctx.ui.notify(reason, "warning");
  });
}
