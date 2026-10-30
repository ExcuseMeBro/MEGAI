# MEGAI Pi action boundary (opt-in until verified live install)

`index.ts` is a Pi `tool_call` approval hook, **not** an OS sandbox, shell parser,
network firewall, or permission system for another process. A user-facing local
confirmation is required for recognized risky model tool calls. Non-interactive
sessions deny those calls with a reason the model can see; a UI error also denies.
It does not retry a failed tool automatically. An exact canonical
`git push origin <40-hex-sha>:refs/heads/dev` avoids *duplicate* approval, but
MEGAI's ownership, accepted-SHA, remote URL and ancestry rules still apply.
Nothing here authorizes a push by itself or relaxes main/publishing approvals.

Recognized categories: recursive destructive file and Git cleanup, push/tag/release,
remote script piping, privilege escalation, and Brokan task/project deletion.
Pi/Paseo process/session stop is blocked, not offered a one-click blanket approval;
ask the owner for fresh explicit permission naming the exact resource and action.
UI confirmation displays the bounded exact
shell command or Brokan target **locally**, never writes it to telemetry. If it
cannot display the subject safely it denies. Ordinary calls and unknown names
remain unaffected to preserve existing coding, web, image, memory and task tools.
This is an *advisory* layer: shell indirection, aliases, files/scripts invoked by
name, direct extension `pi.exec`, other processes, user `!` commands, MCP bridge
internals, and a tool whose name/hints are misleading can bypass its classifier.
Use host permissions/containers and CI/remote branch protections for hard walls.

Tool receipts are JSONL in `~/.megai/private/pi-tool-traces/` (directory 0700,
files 0600), with only timestamp, fixed action/category, bounded safe tool label,
boolean error, and duration. No prompt, arguments, command, output, path, session
ID or token is written. A risky call is denied if the private trace cannot be
written; a completed call cannot be retroactively denied. No raw trace should be
uploaded or attached to a public issue. The extension does not auto-select a
model, loop on failures, impose a spend budget, or silently change Pi settings.

Install only after source-current tests and acceptance: privately back up any
existing target; copy the *whole* `megai-action-boundary/` directory under
`~/.pi/agent/extensions/` and verify a fresh isolated Pi process loads it. Never
run the legacy full `pi-defaults/install.py` simply to install this extension: it
can replace newer packages/settings. Existing Pi sessions require an explicit
user reload to see new extensions; never restart or terminate them for installation.
