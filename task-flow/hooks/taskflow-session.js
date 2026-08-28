#!/usr/bin/env node
/**
 * SessionStart hook — ensures the per-project .todos board exists and feeds its
 * current state into the new session so Claude resumes where it left off.
 *
 *  - If <project>/.todos/ is missing, create it with todo.md / inprogress.md /
 *    done.md (only inside an actual project; never litters home/tmp).
 *  - If it exists, read it and print a short summary as session context so the
 *    in-progress task is resumed and the queue is drained by priority.
 *
 * Output on stdout is injected as SessionStart context by Claude Code.
 * Fail-safe: any error exits 0 so it never blocks session start.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const PROJECT_MARKERS = [
  ".git", "package.json", "pyproject.toml", "go.mod", "Cargo.toml",
  "pom.xml", "build.gradle", "Gemfile", "composer.json", "requirements.txt",
  "CLAUDE.md", ".megai",
];

function readStdin() {
  try { return fs.readFileSync(0, "utf8"); } catch { return ""; }
}

// Walk up from `start` to find the nearest dir holding a project marker.
function findRoot(start) {
  let dir = start;
  for (let i = 0; i < 30; i++) {
    for (const m of PROJECT_MARKERS) {
      try { if (fs.existsSync(path.join(dir, m))) return dir; } catch {}
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

const PMAP = { 1: "low", 2: "medium", 3: "high", 4: "urgent" };
const PRANK = { urgent: 0, high: 1, medium: 2, low: 3 };
const PEMO = { "🔴": "urgent", "🟠": "high", "🟡": "medium", "🟢": "low" };
const SEMO = { "📝": "spec", "📐": "plan", "🔨": "generate", "🧪": "verify", "🔍": "review", "🚀": "ship" };
const P2E = { urgent: "🔴", high: "🟠", medium: "🟡", low: "🟢" };
const S2E = { spec: "📝", plan: "📐", generate: "🔨", verify: "🧪", review: "🔍", ship: "🚀" };

function parseList(txt) {
  const items = [];
  for (const raw of String(txt || "").split("\n")) {
    const m = raw.match(/^\s*[-*]\s+(?:\[[ xX~-]\]\s*)?(.*\S)\s*$/);
    if (!m) continue;
    let rest = m[1].trim(), priority = "medium", stage = "";
    let hit = false;
    for (const e in PEMO) { if (rest.startsWith(e)) { priority = PEMO[e]; rest = rest.slice(e.length).trim(); hit = true; break; } }
    if (!hit) { const pm = rest.match(/^(!{1,4})(?:\s+|$)/); if (pm) { priority = PMAP[pm[1].length]; rest = rest.slice(pm[0].length).trim(); } }
    let shit = false;
    for (const e in SEMO) { if (rest.startsWith(e)) { stage = SEMO[e]; rest = rest.slice(e.length).trim(); shit = true; break; } }
    if (!shit) { const sm = rest.match(/^\(([a-zA-Z]+)\)\s*/); if (sm) { stage = sm[1].toLowerCase(); rest = rest.slice(sm[0].length).trim(); } }
    const text = rest.trim();
    if (text) items.push({ priority, stage, text });
  }
  return items;
}

function main() {
  let cwd = process.cwd();
  const raw = readStdin();
  if (raw) {
    try { const j = JSON.parse(raw); if (j && j.cwd) cwd = j.cwd; } catch {}
  }

  const base = path.join(cwd, ".todos");
  const exists = (() => { try { return fs.existsSync(base); } catch { return false; } })();

  // Only auto-create inside a real project. If a board already exists, honour it
  // wherever it is.
  if (!exists) {
    const root = findRoot(cwd);
    if (!root) return; // not a project — stay silent, don't litter
    create(path.join(root, ".todos"));
    print(path.join(root, ".todos"), true);
    return;
  }
  print(base, false);
}

function create(dir) {
  try {
    fs.mkdirSync(dir, { recursive: true });
    const seed = {
      "todo.md": "# 📋 TODO\n\n",
      "inprogress.md": "# 🚧 IN PROGRESS\n\n",
      "done.md": "# ✅ DONE\n\n",
    };
    for (const [f, body] of Object.entries(seed)) {
      const p = path.join(dir, f);
      if (!fs.existsSync(p)) fs.writeFileSync(p, body, "utf8");
    }
  } catch {}
}

function print(dir, created) {
  let doing = [], pending = [], doneCount = 0;
  try {
    const rd = (f) => {
      try { return fs.readFileSync(path.join(dir, f), "utf8"); } catch { return ""; }
    };
    doing = parseList(rd("inprogress.md"));
    pending = parseList(rd("todo.md")).sort((a, b) => PRANK[a.priority] - PRANK[b.priority]);
    doneCount = parseList(rd("done.md")).length;
  } catch {}

  const lines = [];
  lines.push(
    `[task-flow] ${created ? "created" : "found"} project board: ${dir}`,
  );

  if (!doing.length && !pending.length) {
    lines.push(
      `Board is empty (${doneCount} done). Use the task-flow skill: plan the work, ` +
      `split it into small lines in .todos/todo.md with priority markers, then execute by priority.`,
    );
  } else {
    if (doing.length) {
      lines.push(`🚧 IN PROGRESS (${doing.length}) — resume this first:`);
      for (const t of doing) {
        lines.push(`  ${P2E[t.priority] || "🟡"} ${t.text}${t.stage ? ` ${S2E[t.stage] || ""} ${t.stage}` : ""}`);
      }
    }
    if (pending.length) {
      lines.push(`📋 TODO (${pending.length}, highest priority first):`);
      for (const t of pending.slice(0, 8)) {
        lines.push(`  ${P2E[t.priority] || "🟡"} ${t.text}`);
      }
      if (pending.length > 8) lines.push(`  … (+${pending.length - 8} more)`);
    }
    lines.push(
      `ACTION: re-read .todos/, resume the in-progress tracked task, then drain the queue ` +
      `by priority with risk-scaled ADLC coverage. Invoke the task-flow skill to continue.`,
    );
  }

  process.stdout.write(lines.join("\n") + "\n");

  // Refresh the monitoring dashboard for this board.
  try {
    const { execFileSync } = require("child_process");
    execFileSync(process.execPath, [path.join(__dirname, "taskflow-monitor.js"), dir], { stdio: "ignore" });
  } catch {}
}

try { main(); } catch {}
process.exit(0);
