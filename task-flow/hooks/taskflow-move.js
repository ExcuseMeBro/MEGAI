#!/usr/bin/env node
/**
 * Deterministically move a task line between the .todos board files and refresh
 * monitoring.md. This makes status transitions reliable instead of depending on
 * the model remembering to edit inprogress.md.
 *
 *   taskflow-move.js start <query>   todo.md       -> inprogress.md   ([ ])
 *   taskflow-move.js done  <query>   inprogress/todo -> done.md       ([x])
 *   taskflow-move.js pause <query>   inprogress.md -> todo.md         ([ ])
 *
 * <query> matches by 1-based index in the source list, or case-insensitive
 * substring of the task text. Empty query + start = the first todo task.
 * Fail-safe: errors print a message and exit 0.
 */
"use strict";
const fs = require("fs");
const path = require("path");

function findRoot(start) {
  const markers = [".todos", ".git", "package.json", "pyproject.toml", "go.mod",
    "Cargo.toml", "pom.xml", "CLAUDE.md", ".megai"];
  let dir = start;
  for (let i = 0; i < 40; i++) {
    for (const m of markers) { try { if (fs.existsSync(path.join(dir, m))) return dir; } catch {} }
    const p = path.dirname(dir); if (p === dir) break; dir = p;
  }
  return start;
}

const isTask = (l) => /^\s*[-*]\s+/.test(l);
const taskText = (l) => l.replace(/^\s*[-*]\s+(?:\[[ xX~-]\]\s*)?/, "")
  .replace(/^(?:🔴|🟠|🟡|🟢)\s*/, "").replace(/^(?:📝|📐|🔨|🧪|🔍|🚀)\s*/, "")
  .replace(/^!{1,4}\s*/, "").replace(/^\([a-zA-Z]+\)\s*/, "").trim();

function setCheckbox(line, mark) {
  if (/^\s*[-*]\s+\[[ xX~-]\]/.test(line)) return line.replace(/(\[)[ xX~-](\])/, `$1${mark}$2`);
  return line.replace(/^(\s*[-*]\s+)/, `$1[${mark}] `);
}

function readLines(f) { try { return fs.readFileSync(f, "utf8").replace(/\n+$/, "").split("\n"); } catch { return null; } }
function writeLines(f, lines) { fs.writeFileSync(f, lines.join("\n").replace(/\n+$/, "") + "\n", "utf8"); }

function pick(lines, query) {
  const idx = lines.map((l, i) => ({ l, i })).filter(x => isTask(x.l));
  if (!idx.length) return -1;
  if (!query) return idx[0].i;
  if (/^[A-Za-z]?\d+$/.test(query)) {
    const n = parseInt(query.replace(/^[A-Za-z]/, ""), 10);
    if (n >= 1 && n <= idx.length) return idx[n - 1].i;
  }
  const q = query.toLowerCase();
  const hit = idx.find(x => taskText(x.l).toLowerCase().includes(q));
  return hit ? hit.i : -1;
}

function main() {
  const action = (process.argv[2] || "").toLowerCase();
  const query = (process.argv.slice(3).join(" ") || "").trim();
  if (!["start", "done", "pause"].includes(action)) {
    console.log("usage: taskflow-move.js start|done|pause <query>"); return;
  }
  const base = path.join(findRoot(process.cwd()), ".todos");
  const F = {
    todo: path.join(base, "todo.md"),
    prog: path.join(base, "inprogress.md"),
    done: path.join(base, "done.md"),
  };
  const todo = readLines(F.todo), prog = readLines(F.prog), done = readLines(F.done);
  if (!todo || !prog || !done) { console.log("no .todos board found at " + base); return; }

  let srcArr, srcFile, dstArr, dstFile, mark;
  if (action === "start") { srcArr = todo; srcFile = F.todo; dstArr = prog; dstFile = F.prog; mark = " "; }
  else if (action === "pause") { srcArr = prog; srcFile = F.prog; dstArr = todo; dstFile = F.todo; mark = " "; }
  else { srcArr = prog; srcFile = F.prog; dstArr = done; dstFile = F.done; mark = "x"; }

  let i = pick(srcArr, query);
  // `done` may target a task still in todo.md
  if (i < 0 && action === "done") { srcArr = todo; srcFile = F.todo; i = pick(srcArr, query); }
  if (i < 0) { console.log(`no matching task for "${query || "(first)"}" in ${path.basename(srcFile)}`); return; }

  const line = setCheckbox(srcArr[i], mark);
  srcArr.splice(i, 1);
  dstArr.push(line);
  writeLines(srcFile, srcArr);
  writeLines(dstFile, dstArr);

  try {
    const { execFileSync } = require("child_process");
    execFileSync(process.execPath, [path.join(__dirname, "taskflow-monitor.js"), base], { stdio: "ignore" });
  } catch {}

  const verb = action === "start" ? "▶ started" : action === "pause" ? "⏸ paused" : "✅ done";
  console.log(`${verb}: ${taskText(line)}`);
  console.log(`   ${path.basename(srcFile)} → ${path.basename(dstFile)}`);
}

try { main(); } catch (e) { console.log("taskflow-move: " + (e && e.message)); }
process.exit(0);
