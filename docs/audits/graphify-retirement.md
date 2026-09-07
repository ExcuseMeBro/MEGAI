# Graphify retirement

Removed the Graphify installer, update/status/doctor/guide references, `megai graph`, its background initializer and unused checker. The install pipeline has 12 steps; full project preparation has four core steps. The legacy `MEGAI_SPECIALIST_INDEXES` flag no longer starts jobs. Pi remains lean by default; explicit full preparation preserves agent-memory, codedb and zvec behavior.

## Local removal and recovery

The installed distribution was `graphifyy` 0.9.4 in MEGAI's dedicated `~/.megai/venv/graphify`. Its only discovered launcher in MEGAI/local bin directories was `~/.megai/bin/graphify`. No matching Graphify process or repository Git hook was found. The default package installer registers only the Claude skill and a three-line Claude instruction block; other checked known skill paths were absent.

Archived the full dedicated environment and Claude vendor skill under `~/.graphify-retired/20260907T165956Z/` (0700), outside MEGAI's uninstall scope. Backed up the installer, state, launcher target and Claude instructions. Removed the launcher/installer and only the Graphify state entry. Removed exactly the Claude registration text verified against the installed package's `_skill_registration` template; all surrounding content remained byte-identical.

No Graphify command was executed during removal. Generated graphs, user project files, existing logs and unrelated tools were not deleted. The primary project's `graphify-out/` directory was absent before and after; no fabricated file-preservation count is claimed. Other project data was not scanned or cleaned.

## Verification

The shared retirement test executes actual install/update/status/doctor/uninstall dispatch with a stale Graphify installer and forbidden CLI. It also rejects `megai graph` without invoking the CLI and preserves a sample `graphify-out/graph.json`. Default and legacy-specialist-opt-in preparation both retain only core calls. These regressions fail against preceding source and pass after retirement; Pi runtime, Ruff and related wiring gates protect remaining behavior.

For rollback, reconcile later changes, restore the archived virtual environment to its original path (entry-point shebangs use that path), and restore only selected launcher/skill/registration/state fields. Never overwrite shared configuration wholesale. Generated graph data needs no restoration. Other installations require explicit ownership inspection before archiving vendor skills; source upgrades intentionally do not delete arbitrary external packages or data. Reload old sessions to discard cached skill descriptions.
