// Action-boundary bridge for the ipython tool.
//
// megai-action-boundary classifies `bash` tool calls only. An ipython cell can run shell through
// bash('...'), subprocess, os.system or Path/shutil calls, so before a cell runs we pull the shell
// commands we can see out of the Python source and pass each one through the boundary's own
// classifier. Advisory, like the boundary itself: computed strings, concatenation, eval/exec and
// imported scripts are not visible here.

const SEVERITY = { normal: 0, approval: 1, block: 2 };

/** All Python string literals in `code`, in order, with their decoded text. Comments are skipped. */
export function pythonStrings(code) {
	const out = [];
	let i = 0;
	const n = code.length;
	while (i < n) {
		const ch = code[i];
		if (ch === "#") {
			while (i < n && code[i] !== "\n") i++;
			continue;
		}
		if (ch === "'" || ch === '"') {
			// Prefix letters right before the quote (r, b, f, u, rb, fr, ...).
			let p = i;
			while (p > 0 && /[rRbBuUfF]/.test(code[p - 1]) && p > i - 2) p--;
			if (p > 0 && /[A-Za-z0-9_]/.test(code[p - 1])) p = i; // part of an identifier, not a prefix
			const prefix = code.slice(p, i).toLowerCase();
			const raw = prefix.includes("r");
			const triple = code.startsWith(ch.repeat(3), i);
			const q = triple ? ch.repeat(3) : ch;
			let j = i + q.length;
			let text = "";
			let closed = false;
			while (j < n) {
				if (code.startsWith(q, j)) {
					closed = true;
					break;
				}
				const c = code[j];
				if (!triple && c === "\n") break; // unterminated single-line string
				if (c === "\\" && j + 1 < n) {
					const e = code[j + 1];
					if (raw) text += c + e;
					else text += { n: "\n", t: "\t", r: "\r", "\\": "\\", "'": "'", '"': '"', "\n": "" }[e] ?? c + e;
					j += 2;
					continue;
				}
				text += c;
				j++;
			}
			out.push({ start: p, end: closed ? j + q.length : j, text });
			i = closed ? j + q.length : j;
			continue;
		}
		i++;
	}
	return out;
}

/** Shell commands visible in the cell: every string, string lists (argv), and rmtree paths. */
export function shellCandidates(code) {
	const strings = pythonStrings(code);
	const cands = new Set();
	for (const s of strings) if (s.text.trim()) cands.add(s.text);
	// Mask literals as \u0001<index>\u0001 to find argv lists like ["git", "push", "origin", "main"].
	let masked = "";
	let last = 0;
	strings.forEach((s, k) => {
		masked += code.slice(last, s.start) + `\u0001${k}\u0001`;
		last = s.end;
	});
	masked += code.slice(last);
	const lit = "\u0001(\\d+)\u0001";
	const listRe = new RegExp(`[\\[(]\\s*(${lit}(?:\\s*,\\s*${lit})+)\\s*,?\\s*[\\])]`, "g");
	for (const m of masked.matchAll(listRe)) {
		const parts = [...m[1].matchAll(new RegExp(lit, "g"))].map((x) => strings[Number(x[1])].text);
		cands.add(parts.map((a) => (/^[\w@%+=:,./-]+$/.test(a) ? a : `'${a.replace(/'/g, "'\\''")}'`)).join(" "));
	}
	// Python-native recursive deletes, judged like `rm -rf <path>`.
	const rmRe = new RegExp(`(?:shutil\\.)?rmtree\\(\\s*(?:Path\\(\\s*)?${lit}`, "g");
	for (const m of masked.matchAll(rmRe)) cands.add(`rm -rf ${JSON.stringify(strings[Number(m[1])].text)}`);
	return [...cands];
}

/** Worst boundary verdict over the cell's visible shell commands. */
export function gateDecision(code, classify) {
	let worst = { risk: "normal", category: "unclassified", commands: [] };
	for (const command of shellCandidates(code)) {
		let d;
		try {
			d = classify({ toolName: "bash", input: { command } });
		} catch {
			d = { risk: "approval", category: "uninspectable-shell" };
		}
		if (!d || d.risk === "normal") continue;
		if (SEVERITY[d.risk] > SEVERITY[worst.risk]) worst = { ...d, commands: [command] };
		else if (d.risk === worst.risk) worst.commands.push(command);
	}
	return worst;
}
