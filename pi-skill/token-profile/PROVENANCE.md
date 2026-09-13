# Token profile provenance

Explicit, opt-in profile. This directory ships **compact rewritten adapters** of two
upstream skill texts plus their licenses — not the upstream installers. No upstream
companion skills, hooks, subagents, engines, telemetry or savings claims are included
or executed.

Reviewed upstream cores and licenses are archived read-only at
`~/.megai/artifacts/pi-token-profile-64/upstream/`.

## caveman

- Source: <https://github.com/JuliusBrussee/caveman>
- Reviewed core path: `plugins/caveman/skills/caveman/SKILL.md`
- Distribution reviewed: npm `caveman-installer@2.2.0`
- License of the adapted core: MIT. This adapter is MIT-licensed skill text only; it
  is **not** a copy of the Caveman runtime or the repository as a whole. The
  upstream repository places its Engine-linked directories (`engine/`, `proxy/`,
  `cacheengine/`, `rewriter/`, `browse/`, `mcp/`, `shrink/`, the `cavemem` Go core,
  `shared/platform/`) under BSL-1.1. None of those modules are copied, executed or
  depended on here, and no BSL text or code is shipped.
- Reviewed core `caveman-core.md` sha256:
  `1eddf7055618153869975678d9ff36635602a3aa333f8b4cc0787f12de75b6f8`
- Reviewed `caveman-LICENSE` sha256:
  `f0abc56b6f49ab2e285bb6e6723f028abb7ebd4fe0e242bbdc2b4dded0ace8b9`
  (full text preserved, including its MIT scope note)
- Installed as `skills/caveman/SKILL.md` + `LICENSE.md`.

## ponytail

- Source: <https://github.com/DietrichGebert/ponytail>
- Pin: commit `356918eba965ee1eac64bd3a7f0dd02108350de5`
- License: MIT
- Reviewed core `ponytail-core.md` sha256:
  `1316a2f3f95741d2300b116fe0c2d81ce4a9568656ed0a62643f54aaf09957f2`
- Reviewed `ponytail-LICENSE` sha256:
  `fb1bc6909ac3ef82d5c22106e32ef682b0cff66788fa915fb9b53b15c9d2f3ab`
- Installed as `skills/ponytail/SKILL.md` + `LICENSE.md`.

## Adaptations (accuracy and safety over literal wording)

Both cores were rewritten, not copied, to stay short and to override upstream rules
that trade correctness for terseness:

- Removed the upstream "cuts output tokens 65% (measured)" claim. No universal
  percentage is promised here; any measurement is reported only for the fixture that
  produced it.
- Kept genuine uncertainty. Upstream "drop hedging" is narrowed to filler that carries
  no information; a guess stays a guess and an unverified claim is not stated as fact.
- Kept negations, numbers and units, exact code, commands, error strings and the
  user's language verbatim.
- Ponytail's "code first, at most three lines" output rule is replaced by a
  requested-detail rule: requested reports and explanations arrive complete, and only
  *unrequested* prose is cut.
- Ponytail's reading and test guidance is kept explicit: the ladder shortens the
  solution, never the reading, validation, security, accessibility, requested
  functionality or required checks.
- Persisted artifacts (code, comments, commits, docs, tickets, memory) stay normal
  prose; this profile governs chat style only.
- The MEGAI three-step flow and all approval/acceptance gates are unchanged.

## License filename

Both licenses install as `LICENSE.md`, matching the local caveman filename convention
already tolerated by `lib/slim_wiring.py` (which accepts only `SKILL.md`/`LICENSE.md`
in a local caveman skill). A bare `LICENSE` would make that compatibility check fail
closed. `LICENSE.md` is not discovered as a skill: skill discovery only reads
`SKILL.md` inside a skill directory.

## Non-goals

- No provider/router/telemetry calls; the cores are static text.
- No RTK download, init or trust; RTK is used only through the existing `bash` tool.
- No global shell, settings or `~/.agents` writes.
