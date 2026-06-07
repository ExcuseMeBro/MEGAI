#!/usr/bin/env node
/**
 * Regenerate <project>/.todos/monitoring.md — a live dashboard of task counts
 * by status, priority, and ADLC stage, rendered as pretty markdown tables.
 *
 * Two modes:
 *   - Hook mode (PostToolUse): reads the tool event on stdin. If an Edit/Write
 *     touched a .todos/{todo,inprogress,done}.md file, the sibling
 *     monitoring.md is regenerated so it always reflects the board.
 *   - Direct mode: `taskflow-monitor.js <path-to/.todos>` regenerates that board.
 *
 * Fail-safe: any error exits 0.
 */
"use strict";

const fs = require("fs");
const path = require("path");

const PMAP = { 1: "low", 2: "medium", 3: "high", 4: "urgent" };
const PEMO = { "🔴": "urgent", "🟠": "high", "🟡": "medium", "🟢": "low" };
const SEMO = { "📝": "spec", "📐": "plan", "🔨": "generate", "🧪": "verify", "🔍": "review", "🚀": "ship" };
const P2E = { urgent: "🔴", high: "🟠", medium: "🟡", low: "🟢" };
const S2E = { spec: "📝", plan: "📐", generate: "🔨", verify: "🧪", review: "🔍", ship: "🚀" };
const STAGES = ["spec", "plan", "generate", "verify", "review", "ship"];

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
    if (rest.trim()) items.push({ priority, stage });
  }
  return items;
}

function regenerate(base) {
  let doing, pending, done;
  try {
    const rd = (f) => { try { return fs.readFileSync(path.join(base, f), "utf8"); } catch { return ""; } };
    doing = parseList(rd("inprogress.md"));
    pending = parseList(rd("todo.md"));
    done = parseList(rd("done.md"));
  } catch { return; }

  const open = [...doing, ...pending];
  const pc = { urgent: 0, high: 0, medium: 0, low: 0 };
  for (const t of open) pc[t.priority] = (pc[t.priority] || 0) + 1;
  const sc = {};
  for (const s of STAGES) sc[s] = 0;
  for (const t of doing) if (t.stage && sc[t.stage] !== undefined) sc[t.stage]++;

  const total = doing.length + pending.length + done.length;
  const L = [];
  L.push("# 📊 Task Monitoring");
  L.push("");
  L.push("> Auto-generated from the `.todos` board — do not edit by hand.");
  L.push("");
  L.push(`**Total: ${total}**  ·  🚧 ${doing.length} in progress  ·  📋 ${pending.length} todo  ·  ✅ ${done.length} done`);
  L.push("");
  L.push("## By Status");
  L.push("");
  L.push("| Status | Count |");
  L.push("|:--|--:|");
  L.push(`| 🚧 In Progress | ${doing.length} |`);
  L.push(`| 📋 Todo | ${pending.length} |`);
  L.push(`| ✅ Done | ${done.length} |`);
  L.push(`| **Total** | **${total}** |`);
  L.push("");
  L.push("## Open Tasks by Priority");
  L.push("");
  L.push("| Priority | Count |");
  L.push("|:--|--:|");
  L.push(`| ${P2E.urgent} Urgent | ${pc.urgent} |`);
  L.push(`| ${P2E.high} High | ${pc.high} |`);
  L.push(`| ${P2E.medium} Medium | ${pc.medium} |`);
  L.push(`| ${P2E.low} Low | ${pc.low} |`);
  L.push("");
  L.push("## In Progress by ADLC Stage");
  L.push("");
  L.push("| Stage | Count |");
  L.push("|:--|--:|");
  for (const s of STAGES) L.push(`| ${S2E[s]} ${s} | ${sc[s]} |`);
  L.push("");

  try { fs.writeFileSync(path.join(base, "monitoring.md"), L.join("\n"), "utf8"); } catch {}
}

function main() {
  const arg = process.argv[2];
  if (arg) {
    // Direct mode: arg is a .todos dir (or a project dir containing .todos).
    let base = arg;
    if (path.basename(base) !== ".todos") base = path.join(base, ".todos");
    if (fs.existsSync(base)) regenerate(base);
    return;
  }
  // Hook mode: read the tool event and act only on .todos board edits.
  let raw = "";
  try { raw = fs.readFileSync(0, "utf8"); } catch {}
  if (!raw) return;
  let evt; try { evt = JSON.parse(raw); } catch { return; }
  const ti = evt.tool_input || {};
  const fp = ti.file_path || ti.path || "";
  const m = String(fp).match(/^(.*\/\.todos)\/(?:todo|inprogress|done)\.md$/);
  if (m && fs.existsSync(m[1])) regenerate(m[1]);
}

try { main(); } catch {}
process.exit(0);
