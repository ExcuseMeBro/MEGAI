#!/usr/bin/env node
/**
 * PostToolUse hook — mirrors Claude Code's native Task tools (TaskCreate /
 * TaskUpdate) into a per-session state file the statusline can read in O(1).
 *
 * Native tasks live only in the message stream, not on disk. This hook
 * reconstructs the live list so the statusline can show what's being worked on
 * right now — with activeForm text and per-task timers.
 *
 * State file: ~/.claude/state/tasks/<session_id>.json
 *   { "updated": <epoch ms>, "tasks": [ { id, subject, activeForm,
 *     status, created, started, completed } ] }
 *
 * Fail-safe: any error exits 0 so it never blocks a tool call.
 */
"use strict";

const fs = require("fs");
const path = require("path");

function nowIso() {
  // new Date() with no args is fine in a hook process (not a workflow script).
  return new Date().toISOString();
}

const PRIORITIES = ["low", "medium", "high", "urgent"];
function priorityOf(metadata) {
  const p =
    metadata && typeof metadata.priority === "string"
      ? metadata.priority.toLowerCase()
      : "";
  return PRIORITIES.includes(p) ? p : "medium";
}

// ADLC stages every task moves through.
const STAGES = ["spec", "plan", "generate", "verify", "review", "ship"];
function stageOf(metadata) {
  const s =
    metadata && typeof metadata.stage === "string"
      ? metadata.stage.toLowerCase()
      : "";
  return STAGES.includes(s) ? s : null;
}

function readStdin() {
  try {
    return fs.readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function main() {
  const raw = readStdin();
  if (!raw) return;

  let evt;
  try {
    evt = JSON.parse(raw);
  } catch {
    return;
  }

  const toolName = evt.tool_name || "";
  if (toolName !== "TaskCreate" && toolName !== "TaskUpdate") return;

  const sessionId = String(evt.session_id || "").replace(/[^a-zA-Z0-9_-]/g, "");
  if (!sessionId) return;

  const home = process.env.HOME || process.env.USERPROFILE || "";
  const dir = path.join(home, ".claude", "state", "tasks");
  const file = path.join(dir, sessionId + ".json");

  let state = { updated: 0, tasks: [] };
  try {
    if (fs.existsSync(file)) {
      const parsed = JSON.parse(fs.readFileSync(file, "utf8"));
      if (parsed && Array.isArray(parsed.tasks)) state = parsed;
    }
  } catch {
    // corrupt file — start fresh rather than crash
  }

  const input = evt.tool_input || {};

  if (toolName === "TaskCreate") {
    // The assigned id is not in the input — it comes back in the result string:
    // "Task #N created successfully: <subject>". Fall back to creation order.
    let id = null;
    const resp = evt.tool_response;
    const respStr = typeof resp === "string" ? resp : JSON.stringify(resp || "");
    const m = respStr.match(/#(\d+)/);
    if (m) id = m[1];
    if (!id) {
      const maxId = state.tasks.reduce(
        (mx, t) => Math.max(mx, parseInt(t.id, 10) || 0),
        0,
      );
      id = String(maxId + 1);
    }

    if (!state.tasks.some((t) => String(t.id) === String(id))) {
      state.tasks.push({
        id: String(id),
        subject: input.subject || "",
        activeForm: input.activeForm || "",
        status: "pending",
        priority: priorityOf(input.metadata),
        stage: stageOf(input.metadata) || "spec",
        created: nowIso(),
        started: null,
        completed: null,
      });
    }
  } else if (toolName === "TaskUpdate") {
    const id = String(input.taskId || "");
    const t = state.tasks.find((x) => String(x.id) === id);
    if (t) {
      if (typeof input.subject === "string") t.subject = input.subject;
      if (typeof input.activeForm === "string") t.activeForm = input.activeForm;
      if (input.metadata && typeof input.metadata.priority === "string") {
        t.priority = priorityOf(input.metadata);
      }
      if (input.metadata && typeof input.metadata.stage === "string") {
        const s = stageOf(input.metadata);
        if (s) t.stage = s;
      }
      if (typeof input.status === "string") {
        const st = input.status;
        if (st === "deleted") {
          state.tasks = state.tasks.filter((x) => String(x.id) !== id);
        } else {
          t.status = st;
          if (st === "in_progress" && !t.started) t.started = nowIso();
          if (st === "completed" && !t.completed) t.completed = nowIso();
        }
      }
    }
  }

  state.updated = Date.now();

  try {
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(file, JSON.stringify(state), "utf8");
  } catch {
    // best-effort
  }
}

try {
  main();
} catch {
  // never block a tool call
}
process.exit(0);
