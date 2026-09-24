/** megai-laya-current-0.3.20: offline typed decisions and local file relevance for Pi.
 * Pi's native permissions remain authoritative: no tool_call blocking hook.
 */
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { readFile, realpath, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";
import { registerCompaction } from "./compaction.ts";

const BRIDGE = fileURLToPath(new URL("./bridge.py", import.meta.url));
const PYTHON = () => process.env.LAYA_PYTHON || join(homedir(), ".megai", "laya-runtime", "bin", "python");
const MAX_MESSAGE = 256 * 1024;
const MAX_PATHS = 12;
const MAX_FILE_BYTES = 2 * 1024 * 1024;
const DENY = /(?:^|\/)(?:\.ssh|\.aws|\.gnupg|\.kube|\.docker|\.netrc|_netrc|\.npmrc|\.pypirc)(?:\/|$)|\.config\/gh(?:\/|$)|(?:^|\/)\.env(?:\.|$)|(?:^|\/)id_(?:rsa|dsa|ecdsa|ed25519)|\.(?:pem|key|p12|pfx)$|credential/i;
let worker: ChildProcessWithoutNullStreams | undefined;
let queue: Promise<unknown> = Promise.resolve();
let nextId = 0;

function stop(): void {
  const child = worker;
  worker = undefined;
  if (child && !child.killed) child.kill();
}

function start(): ChildProcessWithoutNullStreams {
  if (worker && worker.exitCode === null && !worker.killed) return worker;
  const child = spawn(PYTHON(), [BRIDGE], {
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, HF_HUB_OFFLINE: "1" },
  });
  // stderr is never protocol and must not become Pi output (e.g. third-party logs).
  child.stderr.resume();
  child.unref();
  child.stdin.unref();
  child.stdout.unref();
  child.stderr.unref();
  worker = child;
  return child;
}

function send(state: string, questions: Record<string, unknown>, signal?: AbortSignal): Promise<any> {
  if (signal?.aborted) return Promise.reject(new Error("local request cancelled"));
  const request = JSON.stringify({ id: ++nextId, state, questions });
  if (Buffer.byteLength(request) + 1 > MAX_MESSAGE) return Promise.reject(new Error("local request exceeds message limit"));
  const cold = !worker || worker.exitCode !== null || worker.killed;
  const child = start();
  const id = nextId;
  return new Promise((done, fail) => {
    let buffer = "";
    let finished = false;
    const requested = Number(process.env.LAYA_TIMEOUT_MS);
    const duration = Number.isFinite(requested) && requested >= 50 ? Math.min(requested, 60_000) : cold ? 60_000 : 15_000;
    const timer = setTimeout(() => finish(new Error("local model timed out")), duration);
    function finish(error?: Error, reply?: any): void {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      child.stdout.off("data", data);
      child.off("error", crash);
      child.off("exit", exit);
      signal?.removeEventListener("abort", abort);
      if (error) { stop(); fail(error); }
      else done(reply);
    }
    function crash(): void { finish(new Error("local model process failed")); }
    function exit(): void { finish(new Error("local model process exited")); }
    function abort(): void { finish(new Error("local request cancelled")); }
    function data(chunk: Buffer): void {
      buffer += chunk.toString("utf8");
      if (Buffer.byteLength(buffer) > MAX_MESSAGE) return finish(new Error("oversized local reply"));
      const newline = buffer.indexOf("\n");
      if (newline < 0) return;
      try {
        const reply = JSON.parse(buffer.slice(0, newline));
        if (reply.ok === true && reply.id !== id) throw new Error("unmatched local reply");
        if (reply.ok !== true) throw new Error(String(reply.error || "local inference failed").slice(0, 200));
        finish(undefined, reply.result);
      } catch (error) {
        finish(error instanceof Error ? error : new Error("invalid local reply"));
      }
    }
    child.stdout.on("data", data);
    child.once("error", crash);
    child.once("exit", exit);
    signal?.addEventListener("abort", abort, { once: true });
    child.stdin.write(request + "\n", (error) => { if (error) finish(new Error("local model pipe failed")); });
  });
}

/** Serialize MPS inference; no unbounded parallel batches or hidden network fallback. */
export function localDecision(state: string, questions: Record<string, unknown>, signal?: AbortSignal): Promise<any> {
  const pending = queue.then(() => send(state, questions, signal));
  queue = pending.catch(() => undefined);
  return pending;
}

function response(value: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(value) }], details: value };
}

export default function laya(pi: ExtensionAPI): void {
  pi.on("session_shutdown", () => stop());
  pi.registerTool({
    name: "laya",
    label: "Laya (local)",
    description: "On-device typed choice, score or noul decisions; advisory only. No hosted Jev fallback.",
    parameters: Type.Object({ state: Type.String(), questions: Type.Record(Type.String(), Type.Any()) }),
    async execute(_id, params, signal) {
      try {
        const answer = await localDecision(params.state, params.questions, signal);
        return response({ ok: true, id: randomUUID().slice(0, 8), model: "laya-multilingual-0.3.20",
          answers: answer.answers, usage: answer.usage });
      } catch (error) {
        return response({ ok: false, error: error instanceof Error ? error.message : "local decision failed" });
      }
    },
  });
  pi.registerTool({
    name: "sift",
    label: "Local file relevance",
    description: "Screen up to 12 readable local files against a query. Unreadable, sensitive and too-long files are not scored.",
    parameters: Type.Object({ query: Type.String(), paths: Type.Array(Type.String()) }),
    async execute(_id, params, signal, _onUpdate, ctx) {
      if (!params.query.trim() || !params.paths.length || params.paths.length > MAX_PATHS)
        return response({ ok: false, error: "query and 1-12 paths required" });
      const files: Array<{ path: string; probability?: number; error?: string }> = [];
      const root = await realpath(ctx.cwd);
      for (const name of params.paths) {
        const entry: { path: string; probability?: number; error?: string } = { path: name };
        files.push(entry);
        try {
          if (!name || DENY.test(name.replaceAll("\\", "/"))) throw new Error("sensitive or empty path");
          const absolute = isAbsolute(name) ? name : resolve(root, name);
          const path = await realpath(absolute);
          if (path !== root && !path.startsWith(root + sep)) throw new Error("outside task directory");
          if (DENY.test(relative(root, path).replaceAll("\\", "/"))) throw new Error("sensitive path");
          const info = await stat(path);
          if (!info.isFile() || info.size > MAX_FILE_BYTES) throw new Error("not a supported text file");
          const bytes = await readFile(path);
          const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
          if (text.includes("\0") || text.length + params.query.length > 20_000) throw new Error("not supported or too long");
          const answer = await localDecision(`Question: ${params.query}\nFile: ${relative(root, path)}\n${text}`,
            { relevant: { type: "noul", instructions: "This file helps answer the question." } }, signal);
          const score = answer.answers?.relevant?.noul;
          if (typeof score !== "number" || !Number.isFinite(score)) throw new Error("invalid local score");
          entry.probability = score;
        } catch (error) {
          entry.error = error instanceof Error ? error.message : "file unavailable";
        }
      }
      return response({ ok: true, files });
    },
  });
  registerCompaction(pi, localDecision);
}
