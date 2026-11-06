# for-ustama — current Pi and Codex setup

This branch contains **only** the safe, current user-level Pi configuration snapshot in [`pi-current/`](pi-current/README.md), plus the Codex (GPT) autonomy files in `pi-current/codex/`. It intentionally does not contain the historical MEGAI source tree, OMP skills, benchmark results, or retired setup files inherited from `dev`.

The snapshot reflects the local setup at the recorded capture time. Credentials, private sessions and third-party installed code are not published; see the snapshot README for exact inclusions, exclusions and reconstruction steps. `dev` and `main` are unaffected by this branch.

## GPT autonomy (Pi + Codex)

GPT models tended to stop with permission or clarifying questions ("qilaymi?", "aniqlashtirib ber") or to report "no changes made" instead of coding. The fix has three layers: autonomy instructions (`pi-current/agent/APPEND_SYSTEM.md`, the closed approval list in `agent/AGENTS.md`, `codex/AGENTS.md`), and a one-shot "decide and finish" continuation when a GPT turn still ends that way: the Pi extension `agent/extensions/megai-keep-going/` and the Codex Stop hook `codex/hooks.json` + `codex/hooks/`. Both share one classifier; tests: `node --experimental-strip-types --test pi-current/tests/keep-going.test.mjs`.
