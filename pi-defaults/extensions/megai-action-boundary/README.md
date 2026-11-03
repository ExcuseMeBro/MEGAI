# MEGAI Pi action boundary

`index.ts` is a Pi `tool_call` approval hook, **not** an OS sandbox, shell parser,
network firewall, or permission system for another process. A user-facing local
confirmation is required for recognized risky model tool calls. Non-interactive
sessions deny those calls with a reason the model can see; a UI error also denies.
It does not retry a failed tool automatically.

STANDING APPROVAL (matches AGENTS.md "Autonomous dev delivery") — these run without a
prompt, also inside multi-line scripts and `cd X && … 2>&1 | tail` chains:
- non-force pushes of any branch except main/master/prod/production/release*/gh-pages or a
  version-like name (also `<sha>`/`"$sha"`/`HEAD:refs/heads/<branch>`, `VAR=1 git push …`);
- deleting a non-protected branch locally (`git branch -d/-D`) or on the remote;
- `git worktree remove [--force] <path>` and `git clean -fd <build-subdir>`;
- `rm -rf` of temp dirs, variables (`"$scratch"`, `${tmp}/out`), relative build output and
  deep absolute paths; root, home, `~/X`, `..`, `*`, `.git`, `$(…)` and `"$x"/*` still prompt;
- `kill <PID>` or `kill "$pid"` (one process). `pkill`/`killall` stay blocked.
Heredoc bodies fed to python/node/psql/cat/… are not parsed as shell; shell heredocs are.
Force pushes, tags, `--all`/`--mirror`, protected branches, `git reset --hard`, bare
`git clean -fdx`, `sudo` and remote-script piping still need a prompt.

Recognized categories: recursive destructive file and Git cleanup, push/tag/release,
remote script piping, privilege escalation, and Brokan task/project deletion.
Broad process stop (`pkill`, `killall`, `launchctl`/`systemctl` stop) is blocked; stopping
one blocking process by exact numeric PID (`kill <PID>`) is allowed without a prompt.
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
