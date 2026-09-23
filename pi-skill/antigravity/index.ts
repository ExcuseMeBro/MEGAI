/**
 * MEGAI Antigravity pool.
 *
 * One self-contained question goes to the installed Antigravity CLI (`agy`) in
 * headless print mode and only its answer comes back. That gives a session a third
 * model pool — the user's Antigravity/Google subscription — next to DeepSeek
 * implementation work and GPT review, without touching another provider's quota or
 * credentials.
 *
 * The wrapper grants no permission, requests plan+sandbox mode and tells `agy` not
 * to use tools: everything the task needs must be inside the prompt. `files` inlines
 * paths the parent already read with native tools. Deliberate ceiling: no agentic
 * repo work or requested writes, and `--dangerously-skip-permissions` is never passed
 * — use interactive `agy` for that.
 */
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { lstatSync, readFileSync, readdirSync, realpathSync, statSync } from "node:fs";
import { isAbsolute, relative, resolve, sep } from "node:path";
import { TextDecoder } from "node:util";
import { Type } from "typebox";

const DEFAULT_BIN = "agy";
const DEFAULT_TIMEOUT_S = 300;
const MAX_TIMEOUT_S = 1_800;
const MAX_FILES = 12;
const MAX_FILE_BYTES = 512 * 1024;
const MAX_CONTEXT_CHARS = 200_000;
const DENIED = /jetski:\s*no output produced|auto-denied|headless mode cannot prompt/i;
const MODEL_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$/;
const NO_TOOLS = "Answer only from this prompt and its supplied context. Do not use tools, commands, external URLs or other files.";
const SENSITIVE_PATH = /(^|[/\\])(?:\.git|\.ssh|\.aws|\.env(?:\.[^/\\]+)?|auth\.json|oauth_creds\.json|credentials?(?:\.(?:json|ya?ml|toml))?|secrets?)(?=$|[/\\])/i;
const SENSITIVE_SUFFIX = /\.(?:pem|key|p12|pfx)$/i;
const UTF8 = new TextDecoder("utf-8", { fatal: true });
const CONTROL = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/;

function decodeText(data: Uint8Array): string | undefined {
  try {
    const text = UTF8.decode(data);
    return CONTROL.test(text) ? undefined : text;
  } catch {
    return undefined;
  }
}

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
      if (SENSITIVE_PATH.test(rel) || SENSITIVE_SUFFIX.test(rel)) {
        notes.push(`${raw}: refused as a credential-like path`);
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
      const text = decodeText(readFileSync(path));
      if (text === undefined) {
        notes.push(`${raw}: skipped, binary content or invalid UTF-8 detected`);
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

type GitCommandResult = { stdout: string; stderr: string; code: number; killed: boolean };

async function git(pi: ExtensionAPI, args: string[], cwd: string): Promise<GitCommandResult> {
  return pi.exec("git", args, { cwd, timeout: 10_000 });
}

function clean(text: string): string {
  return text.trim();
}

function failed(result: GitCommandResult): boolean {
  return result.code !== 0 || result.killed;
}

function worktreePaths(list: string): string[] {
  return list.split(/\r?\n(?=worktree )/)
    .map((entry) => entry.match(/^worktree (.+)$/m)?.[1]?.trim())
    .filter((path): path is string => Boolean(path));
}

function screenWorktreeFiles(root: string): string | undefined {
  const pending = [root];
  let count = 0;
  while (pending.length) {
    const directory = pending.pop()!;
    let entries;
    try {
      entries = readdirSync(directory, { withFileTypes: true });
    } catch {
      return "could not enumerate worktree files";
    }
    for (const entry of entries) {
      const absolute = resolve(directory, entry.name);
      const path = relative(root, absolute);
      let info;
      try {
        info = lstatSync(absolute);
      } catch {
        return `could not inspect worktree path ${path}`;
      }
      // A linked worktree has one root .git metadata file. Nested .git entries
      // are source-controlled escape points and must be rejected, not skipped.
      if (entry.name === ".git") {
        if (directory === root && info.isFile() && !info.isSymbolicLink()) continue;
        return `nested .git entry ${path} cannot be screened safely`;
      }
      const candidates = [path];
      if (info.isSymbolicLink()) {
        let resolved;
        try {
          resolved = realpathSync(absolute);
          const resolvedInfo = statSync(resolved);
          if (resolvedInfo.isDirectory()) return `directory symlink target ${path} cannot be screened safely`;
          const resolvedRelative = relative(root, resolved);
          if (resolvedRelative === ".." || resolvedRelative.startsWith(`..${sep}`) || isAbsolute(resolvedRelative)) {
            return `external symlink target ${path} cannot be screened safely`;
          }
        } catch {
          return `could not resolve symlink target ${path}`;
        }
        candidates.push(resolved);
      }
      if (candidates.some((candidate) => SENSITIVE_PATH.test(candidate) || SENSITIVE_SUFFIX.test(candidate))) {
        return "worktree contains a credential-like path or symlink target";
      }
      if (info.isDirectory()) pending.push(absolute);
      if (++count > 100_000) return "worktree contains too many paths to screen safely";
    }
  }
  return undefined;
}

/** Only linked, clean, non-protected worktrees may receive Agy edits. */
async function verifyDelegationWorktree(pi: ExtensionAPI, parentCwd: string, requested: string) {
  let target: string;
  try {
    target = realpathSync(resolve(parentCwd, requested));
  } catch {
    return { error: "worktree path does not exist or cannot be resolved" };
  }

  const parentRootResult = await git(pi, ["rev-parse", "--show-toplevel"], parentCwd);
  const targetRootResult = await git(pi, ["rev-parse", "--show-toplevel"], target);
  if (failed(parentRootResult) || failed(targetRootResult)) {
    return { error: "both the current directory and worktree must be inside Git repositories" };
  }
  const parentRoot = clean(parentRootResult.stdout);
  const targetRoot = clean(targetRootResult.stdout);
  if (parentRoot === targetRoot) {
    return { error: "refusing the primary checkout; pass a separate linked worktree" };
  }

  const [branchResult, statusResult, listResult, parentCommonResult, targetCommonResult, targetGitDirResult, headResult] =
    await Promise.all([
      git(pi, ["symbolic-ref", "--quiet", "HEAD"], target),
      git(pi, ["status", "--porcelain=v1", "--untracked-files=all"], target),
      git(pi, ["worktree", "list", "--porcelain"], target),
      git(pi, ["rev-parse", "--git-common-dir"], parentRoot),
      git(pi, ["rev-parse", "--git-common-dir"], targetRoot),
      git(pi, ["rev-parse", "--git-dir"], targetRoot),
      git(pi, ["rev-parse", "HEAD"], target),
    ]);
  const branchRef = clean(branchResult.stdout);
  const branch = branchRef.replace(/^refs\/heads\//, "");
  if (failed(branchResult) || !branchRef.startsWith("refs/heads/") || !branch) {
    return { error: "detached HEAD is not allowed for delegated work" };
  }
  if (["refs/heads/main", "refs/heads/dev", "refs/heads/pi", "refs/heads/master"].includes(branchRef)) {
    return { error: `protected branch ${branch} cannot receive delegated edits` };
  }
  if (failed(statusResult)) return { error: "could not inspect worktree status" };
  if (clean(statusResult.stdout)) return { error: "worktree must be clean before delegation" };
  if (failed(listResult)) return { error: "could not verify Git worktree registration" };
  const listed = worktreePaths(listResult.stdout).map((path) => {
    try { return realpathSync(path); } catch { return path; }
  });
  if (!listed.includes(target)) return { error: "path is not a registered linked Git worktree" };
  const primary = listed[0];
  const targetGitDir = clean(targetGitDirResult.stdout);
  const targetCommonDir = clean(targetCommonResult.stdout);
  if (failed(parentCommonResult) || failed(targetCommonResult) || failed(targetGitDirResult)) {
    return { error: "could not inspect Git worktree metadata" };
  }
  if (target === primary || (!failed(targetGitDirResult) && targetCommonDir &&
      resolve(targetRoot, targetGitDir) === resolve(targetRoot, targetCommonDir))) {
    return { error: "refusing Git's primary worktree; pass a separate linked worktree" };
  }
  const fileError = screenWorktreeFiles(target);
  if (fileError) return { error: `${fileError}; refusing to expose it to Agy` };
  if (resolve(parentRoot, clean(parentCommonResult.stdout)) !== resolve(targetRoot, clean(targetCommonResult.stdout))) {
    return { error: "worktree is not attached to the current repository" };
  }
  if (failed(headResult) || !clean(headResult.stdout)) return { error: "could not capture the worktree HEAD" };
  return { target, parentRoot, targetRoot, branch, head: clean(headResult.stdout) };
}

async function delegationResult(pi: ExtensionAPI, target: string, beforeHead: string) {
  const [status, head, diff] = await Promise.all([
    git(pi, ["status", "--short", "--untracked-files=all"], target),
    git(pi, ["rev-parse", "HEAD"], target),
    git(pi, ["diff", "--stat"], target),
  ]);
  const failedCommands = [status, head, diff].filter(failed);
  return {
    auditError: failedCommands.length ? `git audit failed (${failedCommands.map((result) => result.killed ? "killed" : result.code).join(", ")})` : "",
    status: clean(status.stdout),
    diffStat: clean(diff.stdout),
    head: clean(head.stdout),
    commitCreated: Boolean(beforeHead && clean(head.stdout) && beforeHead !== clean(head.stdout)),
  };
}

export default function antigravity(pi: ExtensionAPI) {
  pi.registerTool({
    name: "antigravity",
    label: "Antigravity CLI",
    description: "Send one self-contained prompt to the user's Antigravity CLI (`agy`, Gemini models) " +
      "in headless plan+sandbox mode and return its plain-text answer. The wrapper grants no permissions " +
      "and tells agy not to use tools, so the prompt must carry everything the task needs; pass known paths " +
      "in `files` and their contents are inlined (12 files, 512 KB each, 200 K characters total). Use it " +
      "for a second opinion, a long-context read, research or bulk analysis that should spend the user's " +
      "Antigravity subscription instead of DeepSeek or GPT quota. It never requests edits; interactive " +
      "`agy` is the user's own tool for agentic work.",
    promptSnippet: "Ask the Antigravity CLI (Gemini) one self-contained question and get its answer",
    promptGuidelines: [
      "Use antigravity only for self-contained analysis that should spend the user's Antigravity subscription instead of DeepSeek or GPT quota, inline only the workspace files it needs with `files`, and never send secrets, credentials or personal data.",
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
        minLength: 1, maxLength: 100, pattern: MODEL_ID.source,
        description: "Antigravity model id from `agy models`, e.g. gemini-3.1-pro-high or gemini-3.8-flash-high. Option-like values are refused; omitted keeps the CLI's own default.",
      })),
      timeout_s: Type.Optional(Type.Integer({
        minimum: 5, maximum: MAX_TIMEOUT_S,
        description: `Seconds to wait for the answer (default ${DEFAULT_TIMEOUT_S}, max ${MAX_TIMEOUT_S}).`,
      })),
    }),
    async execute(_id, params, signal, _onUpdate, ctx: ExtensionContext) {
      if (params.model && !MODEL_ID.test(params.model)) {
        return { content: [{ type: "text" as const, text:
          "antigravity: invalid model id; use an exact id from `agy models`, never a CLI option." }] };
      }
      const timeoutS = Math.min(Math.max(params.timeout_s ?? DEFAULT_TIMEOUT_S, 5), MAX_TIMEOUT_S);
      const { block, notes } = inlineFiles(params.files, ctx.cwd);
      const payload = block ? `${params.prompt}\n\nContext files:\n${block}` : params.prompt;
      const args = ["-p", `${NO_TOOLS}\n\n${payload}`, "--mode", "plan", "--sandbox",
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

  pi.registerTool({
    name: "antigravity_delegate",
    label: "Antigravity delegated worker",
    description: "Run a bounded implementation task with Agy in a verified clean linked Git worktree. " +
      "Agy may edit only that worktree in accept-edits+sandbox mode; main/dev/pi, dirty checkouts, detached " +
      "HEADs, commits, pushes and merges are refused. Returns Agy's report plus the worktree diff/status for " +
      "DeepSeek to verify and GPT to review.",
    promptSnippet: "Delegate an implementation task to Antigravity in an isolated linked worktree",
    promptGuidelines: [
      "Use antigravity_delegate only for a bounded implementation subtask with explicit acceptance and a separate linked worktree; never pass the primary checkout or secrets.",
      "DeepSeek remains the coordinating implementer; Agy returns a diff, and GPT reviews the delivered diff and tests before integration.",
    ],
    parameters: Type.Object({
      task: Type.String({
        minLength: 1, maxLength: 100_000,
        description: "Self-contained implementation task with acceptance criteria and focused test expectations.",
      }),
      worktree: Type.String({
        minLength: 1, maxLength: 2_000,
        description: "Existing clean linked Git worktree path, relative to the current directory or absolute.",
      }),
      model: Type.Optional(Type.String({
        minLength: 1, maxLength: 100, pattern: MODEL_ID.source,
        description: "Optional exact Agy model id from `agy models`.",
      })),
      timeout_s: Type.Optional(Type.Integer({ minimum: 5, maximum: MAX_TIMEOUT_S })),
    }),
    async execute(_id, params, signal, _onUpdate, ctx: ExtensionContext) {
      if (params.model && !MODEL_ID.test(params.model)) {
        return { content: [{ type: "text" as const, text: "antigravity_delegate: invalid model id." }] };
      }
      const verified = await verifyDelegationWorktree(pi, ctx.cwd, params.worktree);
      if ("error" in verified) {
        return { content: [{ type: "text" as const, text: `antigravity_delegate refused: ${verified.error}` }] };
      }
      const timeoutS = Math.min(Math.max(params.timeout_s ?? DEFAULT_TIMEOUT_S, 5), MAX_TIMEOUT_S);
      const prompt = [
        "You are the Antigravity implementation worker in a supervised Pi team.",
        "Work only in the current isolated linked worktree. Implement the task below, inspect the real code and run focused tests.",
        "Do not commit, push, merge, change branches, access credentials, or modify anything outside this worktree.",
        "Return a concise report with changed files, tests and results, remaining risks, and any blocker.",
        "The DeepSeek parent will verify your diff and a GPT reviewer will review it before integration.",
        `\nTask:\n${params.task}`,
      ].join("\n");
      const args = ["-p", prompt, "--mode", "accept-edits", "--sandbox", "--print-timeout", `${timeoutS}s`];
      if (params.model) args.push("--model", params.model);
      const bin = process.env.MEGAI_AGY_BIN || DEFAULT_BIN;
      const started = Date.now();
      let result: { stdout?: string; stderr?: string; code?: number | null; killed?: boolean };
      try {
        result = await pi.exec(bin, args, { cwd: verified.target, signal, timeout: (timeoutS + 20) * 1_000 });
      } catch (error) {
        return { content: [{ type: "text" as const, text: `antigravity_delegate: could not run ${bin}: ${error instanceof Error ? error.message : String(error)}` }] };
      }
      const audit = await delegationResult(pi, verified.target, verified.head);
      const seconds = Math.round((Date.now() - started) / 1_000);
      const text = (result.stdout ?? "").trim();
      const detail = { model: params.model ?? "cli default", code: result.code ?? null, seconds,
        worktree: verified.target, branch: verified.branch, ...audit };
      if (audit.auditError) {
        return { content: [{ type: "text" as const, text: `antigravity_delegate: ${audit.auditError}; refusing to report delegated work as verified.` }], details: detail };
      }
      if (audit.commitCreated) {
        return { content: [{ type: "text" as const, text: "antigravity_delegate warning: Agy changed the worktree HEAD; do not integrate until the commit is inspected." }], details: detail };
      }
      if (result.killed) {
        return { content: [{ type: "text" as const, text: `antigravity_delegate: timed out after ${timeoutS}s; inspect the isolated worktree diff.` }], details: detail };
      }
      if (!text || result.code !== 0) {
        const tail = (result.stderr ?? "").trim().slice(-500);
        return { content: [{ type: "text" as const, text: `antigravity_delegate: Agy failed (exit ${result.code ?? "?"}).${tail ? ` stderr: ${tail}` : ""} Inspect the isolated worktree.` }], details: detail };
      }
      return { content: [{ type: "text" as const, text: `${text}\n\n[worktree ${verified.branch}]\n${audit.status || "clean"}\n${audit.diffStat || "no unstaged diff"}` }], details: detail };
    },
  });
}
