import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { homedir } from "node:os";
import { join } from "node:path";
import { StringDecoder } from "node:string_decoder";

const MAX_OUTPUT = 3_000_000;
const root = () => process.env.MEGAI_HOME || join(homedir(), ".megai");

/** Only data on stdin. In particular no provider auth environment reaches Python. */
export function request(action: Record<string, unknown>, cwd: string, signal?: AbortSignal): Promise<any> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new Error("Headroom cancelled"));
    const child = spawn(join(root(), "venv/headroom/bin/python"),
      ["-I", "-B", join(root(), "pi-skill/headroom/bridge.py"), "json"], {
        cwd, stdio: ["pipe", "pipe", "pipe"],
        env: { HOME: homedir(), MEGAI_HOME: root(), PATH: process.env.PATH || "/usr/bin:/bin",
          PYTHONDONTWRITEBYTECODE: "1", PYTHONNOUSERSITE: "1" },
      });
    let output = "";
    const decoder = new StringDecoder("utf8");
    let bytes = 0;
    let settled = false;
    const finish = (error?: Error, value?: unknown) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      signal?.removeEventListener("abort", abort);
      if (error) {
        child.kill("SIGKILL");
        if (action.action === "save") error = new Error(error.message + "; save outcome may be uncertain. Retrying identical text is idempotent.");
      }
      error ? reject(error) : resolve(value);
    };
    const abort = () => finish(new Error("Headroom cancelled"));
    const timer = setTimeout(() => finish(new Error("Headroom timed out; raw context retained")), 30_000);
    signal?.addEventListener("abort", abort, { once: true });
    child.on("error", () => finish(new Error("Headroom unavailable; run megai headroom doctor")));
    child.stdin.on("error", () => finish(new Error("Headroom input failed")));
    // Drain but never forward dependency logs that may include content.
    child.stderr.resume();
    child.stdout.on("data", (chunk: Buffer) => {
      bytes += chunk.length;
      if (bytes > MAX_OUTPUT) return finish(new Error("Headroom response too large"));
      output += decoder.write(chunk);
    });
    child.on("close", (code) => {
      if (code !== 0) return finish(new Error("Headroom failed; run megai headroom doctor"));
      try { finish(undefined, JSON.parse(output + decoder.end())); }
      catch { finish(new Error("Invalid Headroom response")); }
    });
    child.stdin.end(JSON.stringify({ ...action, cwd }));
  });
}

/** Compression never changes source used for edits, mutation receipts, or tests. */
export function discoveryCall(name: string, input: any): boolean {
  if (["ls", "find", "grep"].includes(name)) return true;
  if (name === "mcp" && typeof input?.tool === "string") {
    return /^(?:zvec_grep[_/:])/.test(input.tool);
  }
  if (name !== "bash" || typeof input?.command !== "string") return false;
  const command = input.command.trim();
  if (/[\n\r;&|<>`$()]/.test(command)) return false;
  if (/^(?:ls|rg|find)\s/.test(command)) {
    return !/(?:--pre|--exec|-exec|-delete|-fprint|-fls|-ok)/.test(command);
  }
  const [program, subcommand, ...args] = command.split(/\s+/);
  if (program !== "git") return false;
  const allowed: Record<string, Set<string>> = {
    status: new Set(["--short", "--branch", "-s", "-b", "-sb", "--porcelain", "--porcelain=v1", "--porcelain=v2"]),
    log: new Set(["--oneline", "--graph", "--decorate", "--no-decorate"]),
    "ls-files": new Set(["--cached", "--others", "--exclude-standard", "--stage", "--deleted", "--modified", "-z"]),
  };
  return Boolean(allowed[subcommand]) && args.every(arg => allowed[subcommand].has(arg)
    || (subcommand === "log" && /^(?:-\d+|--max-count=\d+)$/.test(arg)));
}

export default function headroom(pi: ExtensionAPI) {
  // Store only this session's already-sent representations. A stable mapping
  // keeps the provider prefix unchanged without touching native session history.
  const compressed = new Map<string, any>();
  let verbosity: number = 2;
  let steering: string | undefined;
  let warned = false;
  const enabled = () => process.env.MEGAI_HEADROOM !== "0";
  const warn = (ctx: any) => {
    if (!warned) {
      warned = true;
      if (ctx.hasUI) ctx.ui.notify("Headroom unavailable: using raw context. Run megai headroom doctor.", "warning");
      else process.stderr.write("Headroom unavailable: using raw context. Run megai headroom doctor.\n");
    }
  };
  pi.on("session_start", () => {
    compressed.clear(); steering = undefined; warned = false;
    const level = Number(process.env.MEGAI_HEADROOM_VERBOSITY ?? "2");
    verbosity = Number.isInteger(level) && level >= 0 && level <= 4 ? level : 2;
  });
  pi.on("session_shutdown", () => { compressed.clear(); steering = undefined; });
  pi.registerCommand("headroom-verbosity", {
    description: "Headroom concise output: 0 off, 1..4 increasing terseness; thinking stays unchanged",
    handler: async (args, ctx) => {
      const level = Number(args.trim());
      if (!args.trim() || !Number.isInteger(level) || level < 0 || level > 4) {
        if (ctx.hasUI) ctx.ui.notify("Usage: /headroom-verbosity 0..4", "warning");
        return;
      }
      verbosity = level; steering = undefined;
    },
  });
  pi.on("input", (event) => {
    if (/^normal mode\s*$/i.test(event.text.trim())) {
      verbosity = 0; steering = undefined;
    }
  });
  pi.on("before_agent_start", async (event, ctx) => {
    if (!enabled() || verbosity === 0) return;
    try {
      if (steering === undefined) {
        const result = await request({ action: "steering", level: verbosity }, ctx.cwd, ctx.signal);
        if (typeof result.text !== "string") throw new Error("invalid steering");
        steering = result.text;
      }
      return { systemPrompt: event.systemPrompt + "\n\n" + steering +
        "\nReply in the user's language. Preserve uncertainty, safety, full code and requested detail. Explicit style/length requests override terseness." };
    } catch { warn(ctx); }
  });
  pi.on("context", async (event, ctx) => {
    if (!enabled()) return;
    const calls = new Map<string, any>();
    for (const message of event.messages) {
      if (message.role === "assistant") {
        for (const block of message.content) {
          if (block.type === "toolCall") calls.set(block.id, block);
        }
      }
    }
    const messages = [];
    for (const message of event.messages) {
      if (ctx.signal?.aborted) return;
      if (message.role !== "toolResult" || message.isError || message.toolName.startsWith("headroom_")) {
        messages.push(message); continue;
      }
      const call = calls.get(message.toolCallId);
      if (!call || !discoveryCall(call.name, call.arguments) || message.content.length !== 1
          || message.content[0].type !== "text" || message.content[0].text.length < 2000) {
        messages.push(message); continue;
      }
      const text = message.content[0].text;
      const key = createHash("sha256").update(message.toolCallId + "\0" + text).digest("hex");
      if (!compressed.has(key)) {
        try {
          const result = await request({ action: "compress", text }, ctx.cwd, ctx.signal);
          if (typeof result.text !== "string" || (result.compressed && !/^[a-f0-9]{12,64}$/.test(result.id))) {
            throw new Error("invalid compression");
          }
          compressed.set(key, result.compressed ? { ...message, content: [{ type: "text", text: result.text +
            `\n[Headroom compressed. Use headroom_retrieve id=${result.id} for exact original; expires after 7 days. Native session/source remains authoritative.]` }] } : message);
        } catch { compressed.set(key, message); warn(ctx); }
      }
      messages.push(compressed.get(key));
    }
    return { messages };
  });
  pi.registerTool({
    name: "headroom_retrieve", label: "Headroom original",
    description: "Retrieve the exact local original of compressed discovery output, scoped to this repository. Paginate with next_offset; never infer missing evidence.",
    parameters: Type.Object({ id: Type.String(), offset: Type.Optional(Type.Integer({ minimum: 0 })),
      limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 8000 })) }),
    async execute(_id, params, signal, _update, ctx) {
      const result = await request({ action: "retrieve", ...params }, ctx.cwd, signal);
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: {} };
    },
  });
  pi.registerTool({
    name: "headroom_memory", label: "Headroom memory",
    description: "Recall relevant prior decisions, or save only on an explicit user persistence request. Local semantic memory is scoped to this repository, including its worktrees. Saves are limited to 8 KB serialized text. Never save secrets or personal data.",
    parameters: Type.Object({ action: Type.String({ enum: ["recall", "save"] }), text: Type.String({ maxLength: 8000 }) }),
    async execute(_id, params, signal, _update, ctx) {
      const result = await request(params, ctx.cwd, signal);
      return { content: [{ type: "text", text: JSON.stringify(result) }], details: {} };
    },
  });
}
