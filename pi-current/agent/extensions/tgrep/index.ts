import { Type } from "@earendil-works/pi-ai";
import { defineTool, truncateHead, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

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

export default function (pi: ExtensionAPI) {
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
      const outcome = await ctx.executeTool("bash", { command: buildCommand(params, ctx.cwd), timeout: 30 }, { signal });
      if (signal?.aborted) throw new Error("tgrep cancelled.");
      const content = outcome.result.content;
      const text = content.filter((part) => part.type === "text").map((part) => part.text).join("\n");
      const bounded = truncateHead(text, { maxBytes: 24000, maxLines: 400 });
      return {
        content: [{ type: "text", text: `${bounded.content}${bounded.truncated ? "\n[Discovery output truncated; narrow the query or use native bash/rg.]" : ""}\n[Discovery only: read source; native rg is authoritative for completeness.]` }, ...content.filter((part) => part.type !== "text")],
        isError: outcome.isError,
        details: { scope: absolute(ctx.cwd, params.path ?? ctx.cwd), truncated: bounded.truncated, nested: outcome.result.details, indexed: !!params.index_path },
      };
    },
  }));
}
