import { request } from "node:http";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

/** Opt-in observation only. This file never changes a tool result or starts a judge. */
const QUESTION = {
  noise: {
    type: "boolean",
    instructions: "Is this test output mostly repetitive passing/progress lines rather than a useful result, warning, or error?",
  },
};
const MAX_RESPONSE_BYTES = 8192;
const TIMEOUT_MS = 1200;

function testCommand(command: unknown): boolean {
  if (typeof command !== "string" || /[\n\r;&|<>`$()]/.test(command)) return false;
  return /^(?:npm (?:test|run test(?::[\w-]+)?)|node --test|python3? -m (?:pytest|unittest)|pytest)(?:\s|$)/.test(command.trim());
}

/** Fixed loopback destination: no arbitrary URL, HTTP proxy, redirect or credentials. */
function askLocal(port: number, state: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ state, questions: QUESTION });
    const req = request({ hostname: "127.0.0.1", port, path: "/evaluate", method: "POST",
      headers: { "content-type": "application/json", "content-length": Buffer.byteLength(body) } }, (res) => {
      if (res.statusCode !== 200) {
        res.resume();
        reject(new Error("local judge unavailable"));
        return;
      }
      let bytes = 0;
      const chunks: Buffer[] = [];
      res.on("data", (chunk: Buffer) => {
        bytes += chunk.length;
        if (bytes > MAX_RESPONSE_BYTES) {
          req.destroy(new Error("local judge response too large"));
          return;
        }
        chunks.push(chunk);
      });
      res.on("end", () => {
        try {
          const result = JSON.parse(Buffer.concat(chunks).toString("utf8"));
          const answer = result?.answers?.noise;
          const probability = answer?.probability;
          if (result.warnings?.length || answer?.type !== "boolean" ||
              typeof probability !== "number" || !Number.isFinite(probability) ||
              probability < 0 || probability > 1) throw new Error("invalid local judge answer");
          resolve(probability);
        } catch { reject(new Error("invalid local judge answer")); }
      });
    });
    req.setTimeout(TIMEOUT_MS, () => req.destroy(new Error("local judge timeout")));
    req.on("error", reject);
    req.end(body);
  });
}

export default function layaShadow(pi: ExtensionAPI) {
  let generation = 0;
  const pending = new Set<Promise<void>>();
  pi.on("session_start", () => { generation++; });
  pi.on("tool_result", (event) => {
    if (process.env.MEGAI_LAYA_SHADOW !== "1" || event.toolName !== "bash" ||
        event.isError || !testCommand(event.input.command) || event.content.length !== 1 ||
        event.content[0].type !== "text") return;
    const rawPort = process.env.MEGAI_LAYA_SHADOW_PORT || "47823";
    const port = Number(rawPort);
    if (!/^\d{1,5}$/.test(rawPort) || port < 1 || port > 65535) return;
    const text = event.content[0].text;
    if (text.length < 1024) return;
    // Laya has a small context window; only a bounded sample is sent locally.
    const state = text.slice(0, 400) + "\n[...]\n" + text.slice(-500);
    const current = generation;
    const started = Date.now();
    const record = (status: string, probability?: number) => {
      if (current !== generation) return;
      pi.appendEntry("megai.laya.shadow", {
        toolCallId: event.toolCallId, status, ...(probability === undefined ? {} : { probability }),
        inputChars: text.length, elapsedMs: Date.now() - started,
      });
    };
    let work: Promise<void>;
    work = askLocal(port, state)
      .then(probability => record(probability >= 0.8 ? "noise" : probability <= 0.2 ? "useful" : "uncertain", probability))
      .catch(() => { try { record("unavailable"); } catch { /* no session: shadow must stay inert */ } })
      .finally(() => pending.delete(work));
    pending.add(work);
    // Shadow work does not delay the tool result or alter the model's context.
  });
  pi.on("session_shutdown", async () => { await Promise.allSettled([...pending]); });
}
