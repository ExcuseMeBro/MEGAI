#!/usr/bin/env bash
# MEGAI task-flow statusline.
#   line 1  — model · context-window usage · session duration · cost
#   line 2+ — the per-project .todos board (todo / inprogress / done) with
#             priority badges and the active task's ADLC stage.
# Self-contained: reads the statusline JSON on stdin, no external services.
INPUT="$(cat)"
[ -z "$INPUT" ] && INPUT="{}"

NODE_BIN="$(command -v node || true)"
[ -n "$NODE_BIN" ] || exit 0

"$NODE_BIN" -e '
  const fs = require("fs");
  const [, input, cwd] = process.argv;
  const C = {
    reset: "\x1b[0m", dim: "\x1b[2m", bold: "\x1b[1m",
    model: "\x1b[38;5;111m", doing: "\x1b[38;5;114m", pend: "\x1b[38;5;180m",
    done: "\x1b[38;5;108m", warn: "\x1b[38;5;179m", crit: "\x1b[38;5;167m",
    stage: "\x1b[38;5;176m",
  };

  let model = "?", durMs = 0, cost = 0, transcript = "", limit = 200000, cwdJson = "";
  try {
    const j = JSON.parse(input || "{}");
    model = (j.model && (j.model.display_name || j.model.id)) || "?";
    const mid = ((j.model && j.model.id) || "") + ((j.model && j.model.display_name) || "");
    if (/1m|\[1m\]/i.test(mid)) limit = 1000000;
    durMs = (j.cost && j.cost.total_duration_ms) || 0;
    cost = (j.cost && j.cost.total_cost_usd) || 0;
    transcript = j.transcript_path || "";
    cwdJson = (j.workspace && (j.workspace.current_dir || j.workspace.project_dir)) || j.cwd || "";
  } catch {}

  // Context usage: read the most recent usage block from the transcript tail.
  let ctxUsed = 0;
  try {
    if (transcript && fs.existsSync(transcript)) {
      const fd = fs.openSync(transcript, "r");
      const size = fs.fstatSync(fd).size;
      const start = Math.max(0, size - 262144);
      const buf = Buffer.alloc(size - start);
      fs.readSync(fd, buf, 0, buf.length, start);
      fs.closeSync(fd);
      const lines = buf.toString("utf8").split("\n");
      for (let i = lines.length - 1; i >= 0; i--) {
        const ln = lines[i].trim();
        if (!ln) continue;
        let e; try { e = JSON.parse(ln); } catch { continue; }
        const u = e.message && e.message.usage;
        if (u) {
          ctxUsed = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) +
                    (u.cache_creation_input_tokens || 0);
          break;
        }
      }
    }
  } catch {}

  const k = n => n >= 1e6 ? (n / 1e6).toFixed(n % 1e6 ? 1 : 0) + "M"
                : n >= 1e3 ? Math.round(n / 1e3) + "k" : "" + n;
  const dur = ms => {
    const s = Math.floor(ms / 1000), h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    return h ? `${h}h${m}m` : m ? `${m}m` : `${s}s`;
  };
  const pct = limit ? Math.round((ctxUsed / limit) * 100) : 0;
  const ctxC = pct >= 75 ? C.crit : pct >= 50 ? C.warn : C.doing;
  const sep = `  ${C.dim}·${C.reset}  `;
  const out = [];

  out.push(
    `${C.model}◆ ${model}${C.reset}` + sep +
    `◷ ${ctxC}${pct}%${C.reset} ${C.dim}${k(ctxUsed)}/${k(limit)}${C.reset}` + sep +
    `⧗ ${dur(durMs)}` + (cost ? sep + `$${cost.toFixed(2)}` : ""),
  );

  // --- .todos board ---
  const PMAP = { 1: "low", 2: "medium", 3: "high", 4: "urgent" };
  const PRANK = { urgent: 0, high: 1, medium: 2, low: 3 };
  const ADLC = ["spec", "plan", "generate", "verify", "review", "ship"];
  const PEMO = { "🔴": "urgent", "🟠": "high", "🟡": "medium", "🟢": "low" };
  const SEMO = { "📝": "spec", "📐": "plan", "🔨": "generate", "🧪": "verify", "🔍": "review", "🚀": "ship" };
  const P2E = { urgent: "🔴", high: "🟠", medium: "🟡", low: "🟢" };
  const S2E = { spec: "📝", plan: "📐", generate: "🔨", verify: "🧪", review: "🔍", ship: "🚀" };
  const parseList = (txt, status) => {
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
      if (text) items.push({ status, priority, stage, text });
    }
    return items;
  };

  // Resolve session cwd (JSON beats $PWD), then walk UP to the nearest .todos.
  let base = "";
  { let dir = cwdJson || cwd || ".";
    for (let i = 0; i < 40; i++) {
      if (fs.existsSync(dir + "/.todos")) { base = dir + "/.todos"; break; }
      const parent = require("path").dirname(dir);
      if (parent === dir) break;
      dir = parent;
    } }
  if (base && fs.existsSync(base)) {
    const rd = f => { try { return fs.readFileSync(base + "/" + f, "utf8"); } catch { return ""; } };
    const doing = parseList(rd("inprogress.md"), "in_progress");
    const pending = parseList(rd("todo.md"), "pending");
    const doneCount = parseList(rd("done.md"), "completed").length;
    const byPrio = (a, b) => (PRANK[a.priority] ?? 2) - (PRANK[b.priority] ?? 2);
    const open = [...doing.sort(byPrio), ...pending.sort(byPrio)];
    const trim = s => {
      s = String(s || "").replace(/[\r\n\t]+/g, " ").trim();
      return s.length > 44 ? s.slice(0, 43) + "…" : s;
    };
    const badge = t => (P2E[t.priority] || "🟡") + " ";
    const chip = t => (t.stage && S2E[t.stage]) ? `  ${S2E[t.stage]} ${C.stage}${t.stage}${C.reset}` : "";

    if (open.length === 0) {
      out.push(doneCount > 0
        ? `${C.dim}📁 todos${C.reset}  ${C.done}✅ ${doneCount} done${C.reset}  ${C.dim}— board clear${C.reset}`
        : `${C.dim}📁 todos — no tasks${C.reset}`);
    } else {
      const parts = [`${C.dim}📁 todos${C.reset}`];
      if (doing.length)   parts.push(`${C.doing}🚧 ${doing.length}${C.reset}`);
      if (pending.length) parts.push(`${C.pend}📋 ${pending.length}${C.reset}`);
      if (doneCount)      parts.push(`${C.done}✅ ${doneCount}${C.reset}`);
      out.push(parts.join("  "));

      const LIMIT = 3;
      for (const t of open.slice(0, LIMIT)) {
        const isDoing = doing.includes(t);
        const col = isDoing ? `${C.doing}${trim(t.text)}${C.reset}` : `${C.dim}${trim(t.text)}${C.reset}`;
        out.push(`  ${badge(t)}${col}${isDoing ? chip(t) : ""}`);
      }
      if (open.length > LIMIT) out.push(`  ${C.dim}…(+${open.length - LIMIT} more)${C.reset}`);
    }
  }

  process.stdout.write(out.join("\n") + "\n");
' "$INPUT" "$PWD"
