# ipython (Unharnessed tool for Pi)

Unharnessed's persistent Python REPL tool (`ipython`), with its kernel (`unharnessed-runtime`,
`python -m rlm.repl`) running locally. Source: ~/PROJECTS/pi-ipython-bench/pi-ext/ipython-local.
Benchmark that motivated it: ~/PROJECTS/pi-ipython-bench/results/py34-r1/report.md.

- Kernel: ~/.pi/agent/uh-kernel/venv (Python 3.12, freeze in ../../uh-kernel/freeze.txt).
  Override with PI_IPYTHON_PYTHON.
- Safety: every cell's visible shell commands (bash('...'), subprocess argv lists, os.system,
  rmtree paths) go through megai-action-boundary's classify(); risky ones need a confirmation,
  broad process stops are blocked, and the cell fails closed if the boundary cannot load.
  Advisory only: computed strings, eval/exec and scripts run by name are not visible.
- Background bash() completions wake an idle interactive session (`[bash-done pid:N exit:M]`).
- Output capped at 100k chars (tail kept).

Default tools are set in ~/.pi/agent/settings.json ("defaultTools": ["read", "codemode"]):
built-in bash/edit/write are off, read stays so skills keep being listed, extension tools
(ipython, tgrep, web, memory) stay on. Undo: restore backups/settings.json.pre-ipython-*,
or one session with the old tools: `pi-bolt --tools read,bash,edit,write,codemode`.
Disable entirely: move this directory out of extensions/.
