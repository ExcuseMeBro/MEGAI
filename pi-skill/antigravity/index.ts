/**
 * MEGAI Antigravity pool.
 *
 * One self-contained question goes to the installed Antigravity CLI (`agy`) in
 * headless print mode and only its answer comes back. That gives a session a third
 * model pool — the user's Antigravity/Google subscription — next to DeepSeek
 * implementation work and GPT review, without touching another provider's quota or
 * credentials.
 *
 * Headless `agy` cannot answer a permission prompt, so its own tools are auto-denied:
 * everything the task needs must be inside the prompt. `files` inlines paths the
 * parent already read with its native tools. Deliberate ceiling: no agentic repo work
 * and no writes, and `--dangerously-skip-permissions` is never passed — use
 * interactive `agy` for that.
 */
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { readFileSync, realpathSync, statSync } from "node:fs";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { Type } from "typebox";

const DEFAULT_BIN = "agy";
const DEFAULT_TIMEOUT_S = 300;
const MAX_TIMEOUT_S = 1_800;
const MAX_FILES = 12;
const MAX_FILE_BYTES = 512 * 1024;
const MAX_CONTEXT_CHARS = 200_000;
const DENIED = /no output produced|auto-denied|permission/i;
const SENSITIVE_PATH = /(^|[/\\])(?:\.git|\.ssh|\.aws|\.env(?:\.[^/\\]+)?|auth\.json|oauth_creds\.json|credentials?(?:\.(?:json|ya?ml|toml))?|secrets?)(?=$|[/\\])/i;
const SENSITIVE_SUFFIX = /\.(?:pem|key|p12|pfx)$/i;

/** Inline regular text files inside cwd; refuse likely credentials and escapes. */
function inlineFiles(paths: string[] | undefined, cwd: string): { block: string; notes: string[] } {
  const parts: string[] = [];
  const notes: string[] = [];
  let used = 0;
  let root: string;
  try {
    root = realpathSync(cwd);
  } catch (error) {
    return { block: "", notes: [`working directory: ${error instanceof Error ? error.message : String(error)}`] };
  }
  for (const raw of (paths ?? []).slice(0, MAX_FILES)) {
    const input = raw.startsWith("@") ? raw.slice(1) : raw;
    if (SENSITIVE_PATH.test(input) || SENSITIVE_SUFFIX.test(input)) {
      notes.push(`${raw}: refused as a credential-like path`);
      continue;
    }
    try {
      const path = realpathSync(resolve(root, input));
      const rel = relative(root, path);
      if (rel === "" || rel === ".." || rel.startsWith(`..${sep}`) || isAbsolute(rel)) {
        notes.push(`${raw}: refused outside the working directory`);
        continue;
      }
      const info = statSync(path);
      if (!info.isFile()) {
        notes.push(`${raw}: skipped, not a regular file`);
        continue;
      }
      if (info.size > MAX_FILE_BYTES) {
        notes.push(`${raw}: skipped, ${info.size} bytes is over the ${MAX_FILE_BYTES}-byte per-file cap`);
        continue;
      }
      const text = readFileSync(path, "utf8");
      if (text.includes("\0")) {
        notes.push(`${raw}: skipped, binary content detected`);
        continue;
      }
      if (used + text.length > MAX_CONTEXT_CHARS) {
        notes.push(`${raw}: skipped, the ${MAX_CONTEXT_CHARS}-character context budget is spent`);
        continue;
      }
      used += text.length;
      parts.push(`--- ${raw.replace(/[\r\n]/g, " ")} ---\n${text}`);
    } catch (error) {
      notes.push(`${raw}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }
  if ((paths?.length ?? 0) > MAX_FILES) {
    notes.push(`only the first ${MAX_FILES} of ${paths?.length} files were inlined`);
  }
  return { block: parts.join("\n"), notes };
}

export default function antigravity(pi: ExtensionAPI) {
  pi.registerTool({
    name: "antigravity",
    label: "Antigravity CLI",
    description: "Send one self-contained prompt to the user's Antigravity CLI (`agy`, Gemini models) " +
      "in headless mode and return its plain-text answer. Headless `agy` cannot use its own tools — its " +
      "tools are auto-denied without a permission prompt — so the prompt must carry everything the task " +
      "needs; pass known paths in `files` and their contents are inlined (12 files, 512 KB each, 200 K " +
      "characters total). Use it for a second opinion, a long-context read, research or bulk analysis that " +
      "should spend the user's Antigravity subscription instead of DeepSeek or GPT quota. It never edits " +
      "files; interactive `agy` is the user's own tool for agentic work.",
    promptSnippet: "Ask the Antigravity CLI (Gemini) one self-contained question and get its answer",
    promptGuidelines: [
      "Use antigravity for a second opinion, a long-context read or research that should spend the user's Antigravity subscription instead of DeepSeek or GPT quota, inline only the workspace files it needs with `files`, and never send secrets, credentials or personal data.",
    ],
    parameters: Type.Object({
      prompt: Type.String({
        minLength: 1, maxLength: 100_000,
        description: "The complete question or task. Self-contained: headless agy cannot read the repo, run commands or ask a follow-up.",
      }),
      files: Type.Optional(Type.Array(Type.String({ minLength: 1, maxLength: 1_000 }), {
        maxItems: MAX_FILES,
        description: "Regular text files inside the working directory to inline into the prompt. Credential-like, escaping and over-limit paths are refused and reported in `notes`; never send secrets or personal data.",
      })),
      model: Type.Optional(Type.String({
        minLength: 1, maxLength: 100,
        description: "Antigravity model id from `agy models`, e.g. gemini-3.1-pro-high or gemini-3.8-flash-high. Omitted keeps the CLI's own default.",
      })),
      timeout_s: Type.Optional(Type.Integer({
        minimum: 5, maximum: MAX_TIMEOUT_S,
        description: `Seconds to wait for the answer (default ${DEFAULT_TIMEOUT_S}, max ${MAX_TIMEOUT_S}).`,
      })),
    }),
    async execute(_id, params, signal, _onUpdate, ctx: ExtensionContext) {
      const timeoutS = Math.min(Math.max(params.timeout_s ?? DEFAULT_TIMEOUT_S, 5), MAX_TIMEOUT_S);
      const { block, notes } = inlineFiles(params.files, ctx.cwd);
      const args = ["-p", block ? `${params.prompt}\n\nContext files:\n${block}` : params.prompt,
        "--print-timeout", `${timeoutS}s`];
      if (params.model) args.push("--model", params.model);
      const bin = process.env.MEGAI_AGY_BIN || DEFAULT_BIN;
      const started = Date.now();
      let result: { stdout?: string; stderr?: string; code?: number | null; killed?: boolean };
      try {
        result = await pi.exec(bin, args, { signal, timeout: (timeoutS + 20) * 1_000 });
      } catch (error) {
        return { content: [{ type: "text" as const, text:
          `antigravity: could not run ${bin}: ${error instanceof Error ? error.message : String(error)}` }] };
      }
      const seconds = Math.round((Date.now() - started) / 1_000);
      const text = (result.stdout ?? "").trim();
      const detail = { model: params.model ?? "cli default", code: result.code ?? null,
        seconds, files: (params.files ?? []).length, notes };
      if (result.killed) {
        return { content: [{ type: "text" as const, text:
          `antigravity: no answer within ${timeoutS}s (timeout_s). Retry with a larger timeout_s or a smaller prompt.` }], details: detail };
      }
      if (!text) {
        const tail = (result.stderr ?? "").trim().slice(-500);
        return { content: [{ type: "text" as const, text:
          `antigravity: the CLI produced no output (exit ${result.code ?? "?"}).${tail ? ` stderr: ${tail}` : ""}` }], details: detail };
      }
      if (result.code !== 0 || DENIED.test(text)) {
        return { content: [{ type: "text" as const, text:
          `antigravity: the CLI denied or failed the turn, so this answer is not usable evidence. ` +
          `Headless agy auto-denies its own tools without a permission prompt; inline what it needs with \`files\` ` +
          `or use interactive agy. Output:\n${text.slice(0, 2_000)}` }], details: detail };
      }
      return { content: [{ type: "text" as const, text }], details: detail };
    },
  });
}
