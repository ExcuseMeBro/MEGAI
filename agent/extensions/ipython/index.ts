/**
 * Unharnessed's `ipython` tool for everyday Pi use (local kernel, no containers).
 *
 * Port of Unharnessed's tool (crates/uh-core/src/tools/ipython.rs; kernel protocol v3 from
 * unharnessed-runtime/src/rlm/repl.md, commit in SOURCE). Same bootstrap cell, result text and
 * `[bash-done pid:N exit:M]` completion notices as Unharnessed, and its core.md is appended to the
 * system prompt while the tool is active.
 *
 * Local additions:
 * - every cell first passes megai-action-boundary's classifier over the shell commands visible in
 *   the Python source (gate.mjs); risky ones need a UI confirmation, blocked ones never run;
 * - interactive modes never hold a run open for background jobs: a completion notice that becomes
 *   due while the agent is idle starts a turn (`sendMessage` + `triggerTurn`), like Unharnessed;
 *   print/json mode keeps the batch wait at the settle boundary so one-shot runs see the result;
 * - tool text is capped at OUTPUT_CAP_CHARS (tail kept). Unharnessed applies no cap.
 *
 * Kernel: PI_IPYTHON_PYTHON or ~/.pi/agent/uh-kernel/venv/bin/python.
 */
import { spawn, type ChildProcess } from "node:child_process";
import { createInterface } from "node:readline";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { gateDecision } from "./gate.mjs";

const KERNEL_PYTHON = process.env.PI_IPYTHON_PYTHON ?? join(homedir(), ".pi/agent/uh-kernel/venv/bin/python");
const BOUNDARY_DIR = join(homedir(), ".pi/agent/extensions/megai-action-boundary");
const HERE = dirname(fileURLToPath(import.meta.url));
const OUTPUT_CAP_CHARS = 100_000;
const NOTICE_BATCH_MS = 2 * 60 * 1000;
const INTERRUPT_GRACE_MS = 15_000;
const BASH_ACTIVITY_MIME = "application/vnd.unharnessed.bash-activity+json";
const IMAGE_MIME_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];

// Verbatim from crates/uh-core/src/kernel/bootstrap/runtime_code.rs (no Python skills).
const BOOTSTRAP_CODE = `import asyncio
import os as _unharnessed_os

_unharnessed_os.environ["NO_COLOR"] = "1"

try:
    import rlm as _unharnessed_rlm_module
    bash = _unharnessed_rlm_module.bash
    import rlm.mcp as mcp
except Exception as _unharnessed_rlm_error:
    _UNHARNESSED_RLM_IMPORT_ERROR = str(_unharnessed_rlm_error)

    def bash(command):
        raise RuntimeError(
            "unharnessed-runtime is not installed in this kernel. "
            f"Import error: {_UNHARNESSED_RLM_IMPORT_ERROR}"
        )
`;

const KERNEL_RESET_NOTICE =
	"<ipython_kernel_reset>\nThe Python kernel was restarted after a previous interrupted cell kept running. Variables, imports, async tasks, and open resources from before the restart are no longer available; recreate them before using them.\n</ipython_kernel_reset>";

interface CellState {
	id: string;
	stdout: string;
	stderr: string;
	background: string;
	result?: string;
	error?: { ename: string; evalue: string; traceback: string[] };
	attachments: Array<{ mimeType: string; data: string }>;
	status?: "ok" | "error";
	onStream?: (chunk: string) => void;
	resolve: (s: CellState) => void;
	reject: (e: Error) => void;
}

interface Notice {
	pid: number;
	command: string;
	exitCode: number;
	timeoutSeconds?: number;
	at: number;
}

class Kernel {
	private proc?: ChildProcess;
	private starting?: Promise<void>;
	private cells = new Map<string, CellState>();
	private seq = 0;
	private orphanOutput = "";
	private activeCell?: string;
	readonly activities = new Map<string, boolean>();
	notices: Notice[] = [];
	private waiters: Array<() => void> = [];
	restartedSinceLastCall = false;
	everStarted = false;
	stats = { cells: 0, kernelStarts: 0, wakes: 0 };

	private changed() {
		const w = this.waiters;
		this.waiters = [];
		for (const f of w) f();
	}

	private nextChange(ms: number): Promise<void> {
		return new Promise((resolve) => {
			const timer = setTimeout(resolve, Math.max(0, ms));
			this.waiters.push(() => {
				clearTimeout(timer);
				resolve();
			});
		});
	}

	get alive() {
		return !!this.proc && this.proc.exitCode === null && !this.proc.killed;
	}

	private send(obj: unknown) {
		this.proc?.stdin?.write(JSON.stringify(obj) + "\n");
	}

	async ensure(): Promise<void> {
		if (this.alive) return;
		if (!this.starting) {
			this.starting = this.start().finally(() => {
				this.starting = undefined;
			});
		}
		return this.starting;
	}

	cwd = process.cwd();
	onNotice?: () => void;

	private async start(): Promise<void> {
		if (!existsSync(KERNEL_PYTHON)) {
			throw new Error(`ipython kernel not found at ${KERNEL_PYTHON}. Install it (see ~/.pi/agent/extensions/ipython/README.md) or set PI_IPYTHON_PYTHON.`);
		}
		if (this.everStarted) this.restartedSinceLastCall = true;
		this.everStarted = true;
		this.stats.kernelStarts++;
		// Own process group, so a hard kill reaches the kernel's children as well.
		const proc = spawn(KERNEL_PYTHON, ["-m", "rlm.repl"], {
			cwd: this.cwd,
			env: { ...process.env, NO_COLOR: "1" },
			stdio: ["pipe", "pipe", "pipe"],
			detached: true,
		});
		this.proc = proc;
		proc.stdin!.on("error", () => {});
		let stderrTail = "";
		proc.stderr!.on("data", (d) => {
			stderrTail = (stderrTail + d.toString()).slice(-4000);
		});
		const ready = new Promise<void>((resolve, reject) => {
			const timer = setTimeout(() => reject(new Error(`kernel did not become ready: ${stderrTail}`)), 120_000);
			const rl = createInterface({ input: proc.stdout! });
			rl.on("line", (line) => {
				let ev: any;
				try {
					ev = JSON.parse(line);
				} catch {
					return;
				}
				if (ev.event === "ready") {
					clearTimeout(timer);
					resolve();
					return;
				}
				this.onEvent(ev);
			});
			proc.on("exit", (code) => {
				clearTimeout(timer);
				reject(new Error(`kernel exited (${code}): ${stderrTail}`));
				const err = new Error(`Python kernel exited (code ${code}). ${stderrTail.trim()}`);
				for (const c of this.cells.values()) c.reject(err);
				this.cells.clear();
				this.activities.clear();
				this.changed();
			});
		});
		await ready;
		const boot = await this.run(BOOTSTRAP_CODE);
		if (boot.status === "error") {
			throw new Error(`kernel bootstrap failed: ${boot.error?.traceback.join("\n") ?? ""}`);
		}
	}

	private onEvent(ev: any) {
		switch (ev.event) {
			case "stdout":
			case "stderr": {
				const cell = ev.id ? this.cells.get(ev.id) : undefined;
				if (cell) {
					if (ev.event === "stdout") cell.stdout += ev.text;
					else cell.stderr += ev.text;
					cell.onStream?.(ev.text);
				} else {
					const active = this.activeCell ? this.cells.get(this.activeCell) : undefined;
					if (active) active.background += ev.text;
					else this.orphanOutput = (this.orphanOutput + ev.text).slice(-OUTPUT_CAP_CHARS);
				}
				break;
			}
			case "result": {
				const cell = this.cells.get(ev.id);
				if (cell) cell.result = ev.text;
				break;
			}
			case "error": {
				const cell = ev.id ? this.cells.get(ev.id) : undefined;
				if (cell) cell.error = { ename: ev.ename, evalue: ev.evalue, traceback: ev.traceback ?? [] };
				break;
			}
			case "display": {
				const data = ev.data ?? {};
				const activity = data[BASH_ACTIVITY_MIME];
				if (activity && typeof activity.id === "string") {
					this.activities.set(activity.id, !!activity.active);
					if (!activity.active) this.activities.delete(activity.id);
					this.changed();
					this.onNotice?.();
				}
				const cell = ev.id ? this.cells.get(ev.id) : undefined;
				if (cell) {
					for (const mime of IMAGE_MIME_TYPES) {
						if (typeof data[mime] === "string") cell.attachments.push({ mimeType: mime, data: data[mime] });
					}
				}
				break;
			}
			case "host_request": {
				const data = ev.data ?? {};
				if (data.type === "bash.completed") {
					this.notices.push({
						pid: data.pid,
						command: data.command,
						exitCode: data.exitCode,
						timeoutSeconds: data.timeoutSeconds,
						at: Date.now(),
					});
					this.send({ type: "host_reply", id: ev.id, data: { status: "ok", result: {} } });
					this.changed();
					this.onNotice?.();
				} else if (data.type === "bash.consumed") {
					this.notices = this.notices.filter((n) => !(n.pid === data.pid && n.command === data.command));
					this.changed();
				} else {
					this.send({
						type: "host_reply",
						id: ev.id,
						data: { status: "error", error: { message: `unsupported host request ${data.type}` } },
					});
				}
				break;
			}
			case "done": {
				const cell = this.cells.get(ev.id);
				if (cell) {
					cell.status = ev.status;
					this.cells.delete(ev.id);
					if (this.activeCell === ev.id) this.activeCell = undefined;
					cell.resolve(cell);
				}
				break;
			}
		}
	}

	run(code: string, onStream?: (chunk: string) => void): Promise<CellState> {
		const id = `cell-${++this.seq}`;
		return new Promise((resolve, reject) => {
			const cell: CellState = { id, stdout: "", stderr: "", background: "", attachments: [], onStream, resolve, reject };
			cell.background = this.orphanOutput;
			this.orphanOutput = "";
			this.cells.set(id, cell);
			this.activeCell = id;
			this.send({ type: "execute", id, code });
		});
	}

	interrupt(id?: string) {
		this.send(id ? { type: "interrupt", id } : { type: "interrupt" });
	}

	/** Graceful shutdown lets the kernel's atexit hook stop its bash() jobs; then hard-kill the group. */
	kill(): Promise<void> {
		const p = this.proc;
		this.proc = undefined;
		this.notices = [];
		this.activities.clear();
		if (!p || p.exitCode !== null) return Promise.resolve();
		return new Promise((resolve) => {
			const hard = setTimeout(() => {
				try {
					if (p.pid) process.kill(-p.pid, "SIGKILL");
				} catch {}
				resolve();
			}, 5000);
			hard.unref();
			p.once("exit", () => {
				clearTimeout(hard);
				resolve();
			});
			try {
				p.stdin?.end(JSON.stringify({ type: "shutdown" }) + "\n");
			} catch {}
		});
	}

	/** Notices due now: immediately when no command still runs, else after the batch window. */
	takeDue(): Notice[] {
		const oldest = this.notices[0];
		if (!oldest || (this.commandRunning && Date.now() < oldest.at + NOTICE_BATCH_MS)) return [];
		const due = this.notices;
		this.notices = [];
		this.stats.wakes++;
		return due;
	}

	/** Milliseconds until the pending notices become due, or undefined when none are pending. */
	msUntilDue(): number | undefined {
		const oldest = this.notices[0];
		if (!oldest) return undefined;
		return this.commandRunning ? Math.max(0, oldest.at + NOTICE_BATCH_MS - Date.now()) : 0;
	}

	get commandRunning(): boolean {
		for (const active of this.activities.values()) if (active) return true;
		return false;
	}

	/**
	 * At the settle boundary: wait until a notice is due (immediately when no command is still
	 * running, otherwise after the 2-minute batch window), or until nothing can wake the session.
	 */
	async takeWake(deadline: number): Promise<Notice[]> {
		for (;;) {
			const now = Date.now();
			const oldest = this.notices[0];
			if (oldest && (!this.commandRunning || now >= oldest.at + NOTICE_BATCH_MS)) {
				const due = this.notices;
				this.notices = [];
				this.stats.wakes++;
				return due;
			}
			if (!oldest && !this.commandRunning) return [];
			if (now >= deadline) return [];
			const until = oldest ? Math.min(deadline, oldest.at + NOTICE_BATCH_MS) : deadline;
			await this.nextChange(until - now);
		}
	}
}

function formatText(c: CellState): string {
	let text = c.stdout;
	const add = (s: string) => {
		text += (text ? "\n" : "") + s;
	};
	if (c.stderr) add(c.stderr);
	if (c.result !== undefined) add(c.result);
	if (c.status === "error" && c.error) add(c.error.traceback.join("\n"));
	if (c.background) add(`[background output (unattributed)]\n${c.background}`);
	return text;
}

function capOutput(text: string): string {
	if (text.length <= OUTPUT_CAP_CHARS) return text;
	const dropped = text.length - OUTPUT_CAP_CHARS;
	return `[Output truncated: the first ${dropped} of ${text.length} characters were dropped. Keep large data in variables and print only what you need.]\n${text.slice(-OUTPUT_CAP_CHARS)}`;
}

export default function (pi: ExtensionAPI) {
	const kernel = new Kernel();
	const deadline = Number(process.env.PI_IPYTHON_DEADLINE_EPOCH_MS ?? Date.now() + 8 * 3600 * 1000);
	const coreMd = readFileSync(join(HERE, "core.md"), "utf8").trim();
	let lastCtx: any;
	let interactive = false;
	let wakeTimer: ReturnType<typeof setTimeout> | undefined;

	// Load the boundary's classifier. No boundary installed: no gate. Installed but unloadable:
	// fail closed, the same way the boundary treats a decision it cannot make.
	let classify: ((e: unknown) => { risk: string; category: string }) | undefined;
	let classifyError: string | undefined;
	const classifyReady = existsSync(join(BOUNDARY_DIR, "boundary.mjs"))
		? import(pathToFileURL(join(BOUNDARY_DIR, "boundary.mjs")).href).then(
				(m) => {
					classify = m.classify;
					if (typeof classify !== "function") classifyError = "boundary.mjs has no classify()";
				},
				(e) => {
					classifyError = String(e?.message ?? e);
				},
			)
		: Promise.resolve();

	const noticeMessage = (notices: Notice[]) => ({
		customType: "async_bash_completion",
		content: notices
			.map((n) => `[bash-done pid:${n.pid} exit:${n.exitCode}]\n\nCommand: ${JSON.stringify(n.command)}`)
			.join("\n\n"),
		display: true,
		details: notices.map((n) => ({ pid: n.pid, command: n.command, exitCode: n.exitCode, timeoutSeconds: n.timeoutSeconds })),
	});

	// Interactive wake: deliver due notices to an idle session; a busy one picks them up at settle.
	const scheduleWake = () => {
		if (!interactive) return;
		if (wakeTimer) clearTimeout(wakeTimer);
		wakeTimer = undefined;
		const ms = kernel.msUntilDue();
		if (ms === undefined) return;
		wakeTimer = setTimeout(() => {
			wakeTimer = undefined;
			if (!lastCtx?.isIdle?.()) return;
			const due = kernel.takeDue();
			if (due.length) pi.sendMessage(noticeMessage(due), { triggerTurn: true, deliverAs: "followUp" });
			else scheduleWake();
		}, ms + 50);
		wakeTimer.unref?.();
	};
	kernel.onNotice = scheduleWake;

	pi.on("session_start", async (_event, ctx) => {
		lastCtx = ctx;
		interactive = ctx.mode === "tui" || ctx.mode === "rpc";
		kernel.cwd = ctx.cwd ?? process.cwd();
	});

	pi.on("before_agent_start", async (event: any, ctx) => {
		lastCtx = ctx;
		const opts = event.systemPromptOptions;
		const tools: string[] = opts?.selectedTools ?? pi.getActiveTools();
		if (!tools.includes("ipython") || !coreMd) return;
		return { systemPrompt: `${event.systemPrompt}\n\n${coreMd}` };
	});

	pi.on("tool_call", async (event: any, ctx) => {
		if (event.toolName !== "ipython") return;
		await classifyReady;
		if (classifyError) {
			return { block: true, reason: `ipython blocked: the action boundary could not load (${classifyError}). Fix ~/.pi/agent/extensions/megai-action-boundary first.` };
		}
		if (!classify) return;
		const code = String(event.input?.code ?? "");
		const d = gateDecision(code, classify);
		if (d.risk === "normal") return;
		if (d.risk === "block") {
			return { block: true, reason: `Broad process stop blocked (${d.category}): ${d.commands.join(" | ").slice(0, 300)}. Stop only the exact blocking process with kill <PID>; do not retry.` };
		}
		const subject = d.commands.join("\n").slice(0, 1024);
		let approved = false;
		if (ctx?.hasUI && typeof ctx.ui?.confirm === "function" && !/[\x00-\x08\x0b-\x1f\x7f]/.test(subject)) {
			try {
				approved = (await ctx.ui.confirm("Approve risky ipython cell?", `${d.category}: ipython\n${subject}`)) === true;
			} catch {}
		}
		if (!approved) {
			return { block: true, reason: `Risky ipython cell not approved (${d.category}): ${subject.slice(0, 300)}. Request explicit interactive approval. No automatic retry.` };
		}
	});

	pi.registerTool({
		name: "ipython",
		label: "ipython",
		description: "Run Python code in the persistent REPL.",
		promptSnippet: "ipython - persistent Python REPL for code, state, and bash() orchestration",
		executionMode: "sequential",
		parameters: Type.Object({
			code: Type.String({ description: "Python code to run." }),
		}),
		async execute(_toolCallId, params, signal, onUpdate, ctx) {
			const code = (params as { code: string }).code;
			if (ctx) lastCtx = ctx;
			await kernel.ensure();
			let restarted = kernel.restartedSinceLastCall;
			kernel.restartedSinceLastCall = false;
			kernel.stats.cells++;
			const started = Date.now();
			const cellPromise = kernel.run(code, (chunk) =>
				onUpdate?.({ content: [{ type: "text", text: chunk }], details: { status: "ok" } }),
			);
			let aborted = false;
			const onAbort = () => {
				aborted = true;
				kernel.interrupt();
				setTimeout(() => {
					if (aborted) kernel.kill();
				}, INTERRUPT_GRACE_MS).unref();
			};
			signal?.addEventListener("abort", onAbort, { once: true });
			let cell: CellState;
			try {
				cell = await cellPromise;
			} catch (e) {
				signal?.removeEventListener("abort", onAbort);
				throw e;
			} finally {
				aborted = false;
			}
			signal?.removeEventListener("abort", onAbort);
			let text = formatText(cell);
			if (restarted) text = text ? `${KERNEL_RESET_NOTICE}\n\n${text}` : KERNEL_RESET_NOTICE;
			const content: any[] = [{ type: "text", text: capOutput(text) }];
			for (const a of cell.attachments) content.push({ type: "image", data: a.data, mimeType: a.mimeType });
			const isError = cell.status === "error";
			const details = {
				status: cell.status ?? "ok",
				kernelRestarted: restarted,
				durationMs: Date.now() - started,
				errorEname: cell.error?.ename,
			};
			if (isError) {
				// Pi marks a tool result as an error when execute throws; keep the full text visible.
				const err = new Error(capOutput(text) || cell.error?.ename || "error");
				(err as any).details = details;
				throw err;
			}
			return { content, details };
		},
	});

	pi.on("agent_before_settle", async (event, ctx) => {
		lastCtx = ctx;
		if (!kernel.everStarted) return;
		// Interactive: take what is due now; later notices wake the idle session (scheduleWake).
		// One-shot print/json runs: wait here, or the process would exit before jobs finish.
		const notices = interactive ? kernel.takeDue() : await kernel.takeWake(deadline);
		if (interactive) scheduleWake();
		if (notices.length === 0) return;
		return { entries: [...(event.entries ?? []), { type: "custom_message", ...noticeMessage(notices) }], continue: true };
	});

	pi.on("session_shutdown", async () => {
		if (wakeTimer) clearTimeout(wakeTimer);
		await kernel.kill();
	});
}
