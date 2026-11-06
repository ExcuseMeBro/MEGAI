# for-ustama — current Pi and Codex setup

This branch contains **only** the safe, current user-level Pi configuration snapshot in [`pi-current/`](pi-current/README.md), plus the Codex (GPT) autonomy files in `pi-current/codex/`. It intentionally does not contain the historical MEGAI source tree, OMP skills, benchmark results, or retired setup files inherited from `dev`.

The snapshot reflects the local setup at the recorded capture time. Credentials, private sessions and third-party installed code are not published; see the snapshot README for exact inclusions, exclusions and reconstruction steps. `dev` and `main` are unaffected by this branch.

## GPT autonomy (Pi + Codex)

GPT models tended to stop with permission or clarifying questions ("qilaymi?", "aniqlashtirib ber") or to report "no changes made" instead of coding. The fix has three layers: autonomy instructions (`pi-current/agent/APPEND_SYSTEM.md`, the closed approval list in `agent/AGENTS.md`, `codex/AGENTS.md`), and a one-shot "decide and finish" continuation when a GPT turn still ends that way: the Pi extension `agent/extensions/megai-keep-going/` and the Codex Stop hook `codex/hooks.json` + `codex/hooks/`. Both share one classifier; tests: `node --experimental-strip-types --test pi-current/tests/keep-going.test.mjs`.

## Faster runs at the same quality

Measured on one prompt (gpt-6.1-sol): system prompt 77.7k → 36k chars, input tokens per request 23,767 → 13,501 (−43%), with skill routing verified.

- `agent/extensions/megai-lean-prompt/`: keeps full skill entries only for frequently used skills (`config.json`) and lists the other ~80 as one-line `name: trigger` entries. Skills listing was ~75% of every request; all skills stay loadable.
- `agent/skills/diff-security/`: a 3k-char diff security checklist for every code change, replacing the full 22k-char `security-audit` load (159 loads in recent sessions); high-risk diffs still escalate to `security-audit` guidance plus one companion file.
- `agent/APPEND_SYSTEM.md` "Default loop": scope → decide → build → focused tests → one review + `diff-security` → deliver → ≤10-line report, with speed rules (batch reads, no narration, no redundant reruns).

Tests: `node --experimental-strip-types --test pi-current/tests/*.test.mjs`.
