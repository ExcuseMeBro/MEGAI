#!/usr/bin/env node
/**
 * Deterministically move a task between the .todos board files and advance its
 * ADLC stage, then refresh monitoring.md. Removes reliance on the model
 * remembering to edit inprogress.md or the stage emoji.
 *
 *   taskflow-move.js start <query>            todo  -> inprogress (stage = 📝 spec)
 *   taskflow-move.js done  <query>            inprogress/todo -> done ([x])
 *   taskflow-move.js pause <query>            inprogress -> todo
 *   taskflow-move.js stage <stage|next> [q]   set/advance the in-progress task's stage
 *
 * <query> = 1-based index in the source list, or case-insensitive substring.
 * Empty query = the first task. Fail-safe: errors print a message and exit 0.
 */
"use strict";
const fs = require("fs");
const path = require("path");

const PRIOS = ["🔴", "🟠", "🟡", "🟢"];
const S2E = { spec: "📝", plan: "📐", generate: "🔨", verify: "🧪", review: "🔍", ship: "🚀" };
const STAGE_ORDER = ["spec", "plan", "generate", "verify", "review", "ship"];
const STAGE_EMOS = Object.values(S2E);
const E2S = Object.fromEntries(Object.entries(S2E).map(([k, v]) => [v, k]));

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

// Split a task line into its parts so we can rebuild it cleanly.
function parseLine(line) {
  const m = line.match(/^(\s*[-*]\s+)(\[[ xX~-]\]\s*)?(.*)$/);
  let prefix = m ? m[1] : "- ";
  let box = m && m[2] ? m[2].trim() + " " : "";
  let rest = (m ? m[3] : line).trim();
  let prio = "";
  for (const e of PRIOS) { if (rest.startsWith(e)) { prio = e; rest = rest.slice(e.length).trim(); break; } }
  let stage = "";
  for (const e of STAGE_EMOS) { if (rest.startsWith(e)) { stage = e; rest = rest.slice(e.length).trim(); break; } }
  return { prefix, box, prio, stage, text: rest.trim() };
}
function buildLine(p) {
  const body = [p.prio, p.stage, p.text].filter(Boolean).join(" ");
  return (p.prefix + p.box + body).replace(/\s+$/, "");
}
const taskText = (l) => parseLine(l).text;

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

function refreshMonitor(base) {
  try {
    const { execFileSync } = require("child_process");
    execFileSync(process.execPath, [path.join(__dirname, "taskflow-monitor.js"), base], { stdio: "ignore" });
  } catch {}
}

function boardFiles(base) {
  return { todo: path.join(base, "todo.md"), prog: path.join(base, "inprogress.md"), done: path.join(base, "done.md") };
}

function doStage(base, arg, query) {
  const F = boardFiles(base);
  const prog = readLines(F.prog);
  if (!prog) { console.log("no inprogress.md at " + base); return; }
  const i = pick(prog, query);
  if (i < 0) { console.log(`no in-progress task matching "${query || "(first)"}"`); return; }
  const p = parseLine(prog[i]);
  const cur = p.stage ? E2S[p.stage] : "";
  let next;
  if (arg === "next" || arg === "+") {
    const ci = cur ? STAGE_ORDER.indexOf(cur) : -1;
    next = STAGE_ORDER[Math.min(ci + 1, STAGE_ORDER.length - 1)];
  } else if (STAGE_ORDER.includes(arg)) {
    next = arg;
  } else {
    console.log(`unknown stage "${arg}" (use: ${STAGE_ORDER.join(" ")} | next)`); return;
  }
  p.stage = S2E[next];
  prog[i] = buildLine(p);
  writeLines(F.prog, prog);
  refreshMonitor(base);
  console.log(`◐ stage: ${taskText(prog[i])} → ${S2E[next]} ${next}`);
}

function main() {
  const action = (process.argv[2] || "").toLowerCase();
  const a3 = process.argv[3] || "";
  if (!["start", "done", "pause", "stage"].includes(action)) {
    console.log("usage: taskflow-move.js start|done|pause <query> | stage <stage|next> [query]"); return;
  }
  const base = path.join(findRoot(process.cwd()), ".todos");

  if (action === "stage") {
    doStage(base, a3.toLowerCase(), process.argv.slice(4).join(" ").trim());
    return;
  }

  const query = process.argv.slice(3).join(" ").trim();
  const F = boardFiles(base);
  const todo = readLines(F.todo), prog = readLines(F.prog), done = readLines(F.done);
  if (!todo || !prog || !done) { console.log("no .todos board found at " + base); return; }

  let srcArr, srcFile, dstArr, dstFile;
  if (action === "start") { srcArr = todo; srcFile = F.todo; dstArr = prog; dstFile = F.prog; }
  else if (action === "pause") { srcArr = prog; srcFile = F.prog; dstArr = todo; dstFile = F.todo; }
  else { srcArr = prog; srcFile = F.prog; dstArr = done; dstFile = F.done; }

  let i = pick(srcArr, query);
  if (i < 0 && action === "done") { srcArr = todo; srcFile = F.todo; i = pick(srcArr, query); }
  if (i < 0) { console.log(`no matching task for "${query || "(first)"}" in ${path.basename(srcFile)}`); return; }

  const p = parseLine(srcArr[i]);
  if (action === "start") { p.box = "[ ] "; if (!p.stage) p.stage = S2E.spec; }   // entering ADLC at spec
  else if (action === "pause") { p.box = "[ ] "; }
  else { p.box = "[x] "; }                                                        // done
  const line = buildLine(p);

  srcArr.splice(i, 1);
  dstArr.push(line);
  writeLines(srcFile, srcArr);
  writeLines(dstFile, dstArr);
  refreshMonitor(base);

  const verb = action === "start" ? "▶ started" : action === "pause" ? "⏸ paused" : "✅ done";
  console.log(`${verb}: ${p.text}`);
  console.log(`   ${path.basename(srcFile)} → ${path.basename(dstFile)}`);
}

try { main(); } catch (e) { console.log("taskflow-move: " + (e && e.message)); }
process.exit(0);
