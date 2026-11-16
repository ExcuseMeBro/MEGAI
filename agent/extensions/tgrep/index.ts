import { Type } from "@earendil-works/pi-ai";
import { defineTool, truncateHead, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { guardBroadSearch } from "./search-policy.mjs";

const quote = (s: string) => `'${s.replaceAll("'", "'\\''")}'`;
export interface SearchParams {
  pattern?: string;
  regex?: boolean;
  path?: string;
  glob?: string;
  per_file?: number;
  index_path?: string;
}
const absolute = (cwd: string, p: string) => p === "~" ? homedir() : p.startsWith("~/") ? join(homedir(), p.slice(2)) : resolve(cwd, p);

export function buildCommand(params: SearchParams, cwd: string): string {
  if (params.pattern === undefined && !params.glob?.trim()) throw new Error("Supply pattern for content search or glob for filename discovery.");
  if (params.pattern === "") throw new Error("Empty patterns are not supported; narrow the search.");
  const scope = absolute(cwd, params.path ?? cwd);
  const args = params.pattern === undefined
    ? ["--files"]
    : ["-nH", "--no-heading", "--color", "never", "--smart-case", "--max-count", String(params.per_file ?? 5), ...(params.regex ? [] : ["-F"])];
  if (params.glob) args.push("--glob", params.glob);
  const tail = [...args, "--", ...(params.pattern === undefined ? [] : [params.pattern]), scope];
  const rg = ["rg", "--max-filesize", "64M", ...tail].map(quote).join(" ");
  const indexed = params.index_path ? ["--index-path", absolute(cwd, params.index_path)] : ["--no-index"];
  const native = ["tgrep", ...indexed, ...tail].map(quote).join(" ");
  // Explicit indexes are opt-in and task-owned. Never build indexes or start servers here.
  const readiness = params.index_path ? `
    status=$(tgrep --index-path ${quote(absolute(cwd, params.index_path))} status ${quote(scope)} 2>&1)
    status_code=$?
    if [ "$status_code" -ne 0 ] || ! printf '%s\\n' "$status" | grep -Eq '^[[:space:]]*Indexing:[[:space:]]+complete[[:space:]]*$'; then
      printf '%s\\n' "$status" >&2
      printf '%s\\n' '[tgrep] Explicit index/server not ready; native rg fallback.' >&2
      use_tgrep=0
    fi` : "";
  return `use_tgrep=0
if command -v tgrep >/dev/null 2>&1; then
  use_tgrep=1${readiness}
else
  printf '%s\\n' '[tgrep] Executable unavailable; native rg fallback.' >&2
fi
if [ "$use_tgrep" -eq 1 ]; then
  printf '%s\\n' ${quote(`[backend=tgrep; mode=${params.index_path ? "explicit-index" : "live-scan"}]`)} >&2
  ${native}
  code=$?
  if [ "$code" -eq 0 ]; then exit 0; fi
  if [ "$code" -eq 1 ]; then printf '%s\\n' '[exit=1: no matches in searched coverage; not proof of absence]'; exit 0; fi
  printf '[tgrep] Failed with exit %s; native rg fallback follows.\\n' "$code" >&2
fi
printf '%s\\n' '[backend=rg-fallback; max-filesize=64M]' >&2
${rg}
code=$?
if [ "$code" -eq 1 ]; then printf '%s\\n' '[exit=1: no matches in searched coverage; not proof of absence]'; exit 0; fi
exit "$code"`;
}

const SEARCH_TIMEOUT_MS = 30_000;
const MAX_CAPTURE_BYTES = 4 * 1024 * 1024;

// Run the search script directly. It must not depend on the `bash` tool: sessions and
// children with a tool allowlist (e.g. --tools tgrep) do not have it.
export function runSearch(command: string, cwd: string, signal?: AbortSignal): Promise<{ text: string; code: number | null }> {
  return new Promise((done, fail) => {
    const child = spawn("bash", ["-c", command], { cwd, detached: true, stdio: ["ignore", "pipe", "pipe"] });
    const chunks: Buffer[] = [];
    let size = 0, clipped = false, stoppedBy = "";
    const take = (chunk: Buffer) => { if (size < MAX_CAPTURE_BYTES) { chunks.push(chunk); size += chunk.length; } else clipped = true; };
    child.stdout.on("data", take);
    child.stderr.on("data", take);
    // Kill the whole process group so tgrep/rg do not outlive bash.
    const stop = (reason: string) => { stoppedBy ||= reason; try { process.kill(-child.pid!, "SIGKILL"); } catch { child.kill("SIGKILL"); } };
    const timer = setTimeout(() => stop("the 30 s limit"), SEARCH_TIMEOUT_MS);
    const abort = () => stop("cancellation");
    signal?.addEventListener("abort", abort, { once: true });
    const finish = () => { clearTimeout(timer); signal?.removeEventListener("abort", abort); };
    child.on("error", (error) => { finish(); fail(error); });
    child.on("close", (code) => {
      finish();
      let text = Buffer.concat(chunks).toString("utf8");
      if (clipped) text += "\n[tgrep] Output exceeded 4 MiB; showing the first part only.";
      if (stoppedBy) text += `\n[tgrep] Search stopped by ${stoppedBy}; narrow the path or pattern.`;
      done({ text, code: stoppedBy ? null : code });
    });
  });
}

export default function (pi: ExtensionAPI) {
  // Best-effort Pi tool-call guard, not a shell sandbox or a user command interceptor.
  pi.on("tool_call", (event) => guardBroadSearch(event));
  pi.registerTool(defineTool({
    name: "tgrep",
    label: "tgrep",
    description: "Default local literal/regex code discovery and filename glob search. Smart-case, literal by default. Uses live tgrep scans unless a ready task-owned external index_path is explicitly supplied; no startup indexing or daemon. Errors/unavailable indexes fall back to native rg with diagnostics. Default coverage excludes ignored/hidden/binary and >64MiB files. Not an authoritative absence/completeness check. Filename glob is not fuzzy search.",
    promptSnippet: "Default local code discovery via tgrep; filename globs",
    promptGuidelines: [
      "Use tgrep first for code discovery; use glob without pattern for filename discovery and read to inspect source. This user-selected default replaces FSearch.",
      "Keep native rg for exhaustive/current references, absence, excluded files, acceptance/security checks and unsupported semantics. Empty, truncated or indexed results never prove completeness.",
      "Default tgrep tool uses live scans without writes. For repeated searches, explicitly prepare a task-owned external index/server via bash; supply index_path only after verifying its root, options, ownership and readiness. Stop only servers you own; never index the whole home or start indexing at Pi launch.",
    ],
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    parameters: Type.Object({
      pattern: Type.Optional(Type.String({ minLength: 1, description: "Content pattern; omit for filename glob search." })),
      regex: Type.Optional(Type.Boolean({ description: "Regex instead of literal; default false, smart-case." })),
      path: Type.Optional(Type.String({ description: "Scope; cwd-relative, absolute or ~/. Defaults to cwd." })),
      glob: Type.Optional(Type.String({ minLength: 1, description: "Filename glob/filter, e.g. **/*.ts or *queue*.py. Not fuzzy search." })),
      per_file: Type.Optional(Type.Integer({ minimum: 1, maximum: 100, description: "Maximum matching lines per file, default 5. Results may be incomplete." })),
      index_path: Type.Optional(Type.String({ minLength: 1, description: "Optional ready task-owned external index with matching root/options and server. Omit for live scan; never reuse an unknown index." })),
    }),
    async execute(_id, params, signal, _update, ctx) {
      if (signal?.aborted) throw new Error("tgrep cancelled.");
      // A missing scope fails in both tgrep and rg; report it once instead of a fallback.
      const scope = absolute(ctx.cwd, params.path ?? ctx.cwd);
      if (!existsSync(scope)) throw new Error(`tgrep path not found: ${scope}. Check the path or search its parent directory.`);
      const { text, code } = await runSearch(buildCommand(params, ctx.cwd), ctx.cwd, signal);
      if (signal?.aborted) throw new Error("tgrep cancelled.");
      const bounded = truncateHead(text, { maxBytes: 24000, maxLines: 400 });
      const exit = code === 0 ? "" : `\n[tgrep] Search failed (exit ${code ?? "killed"}); this is not a zero-match result.`;
      return {
        content: [{ type: "text", text: `${bounded.content}${bounded.truncated ? "\n[Discovery output truncated; narrow the query or use native bash/rg.]" : ""}${exit}\n[Discovery only: read source; native rg is authoritative for completeness.]` }],
        isError: code !== 0,
        details: { scope, truncated: bounded.truncated, exitCode: code, indexed: !!params.index_path },
      };
    },
  }));
}
