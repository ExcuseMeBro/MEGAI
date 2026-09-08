# Tgrep text discovery

Use native `tgrep` first for literal/regex discovery against a ready, task-owned index. Keep codedb for structure and zvec for intent; neither is replaced. This default applies to Pi parents and children. It does not rewrite shell commands, replace Pi tools, or change repository verification commands.

## Query

```bash
tgrep -nH --color never -F 'literal' .
tgrep -nH --color never 'regex' .
```

Scope to relevant paths and read the source before making changes. Use native `rg` with the intended flags if tgrep is absent, errors, has no ready index/server, or differs from required rg semantics (including config, encoding, binary/archive handling, traversal and size limits). Report the fallback. A failed command is not a zero-match result; preserve its diagnostics and exit code. Never pass a tgrep-only flag to rg.

## On-demand index and server

Check `tgrep status /absolute/root` only when indexed text discovery is relevant. A running server must report `Indexing: complete` before using it. Servers can answer from partial data while starting. Status is a readiness hint, not a freshness certificate.

For repeated searches that justify preparation, build with `tgrep index /absolute/root`, then run `tgrep serve /absolute/root` as a task-owned foreground process (or through an explicitly managed task process). Use identical traversal/size/index-path options for index, serve and search. Use the upstream cache default or a private external index directory, never an unrelated existing index. Reuse only a server whose root, options and ownership are known. Stop only the process you started when the task ends. Installation, doctor, Pi launch and skill loading never index, start a server, or warm a model.

Default tgrep file-size coverage is 64 MiB, unlike rg's uncapped default. For authoritative coverage use rg; choose `--no-max-filesize` consistently for index/serve/search only when unlimited indexing is explicitly appropriate to this corpus.

## Freshness and acceptance

Watchers are eventually consistent and can miss events. After edits, added/deleted/renamed files, branch switches, changed ignore rules or watcher warnings, use rg for affected discovery until a completed rebuild and server restart is known to cover the current tree. Children inherit this rule; a parent-prepared index does not prove later child writes are visible.

Confirm absence claims, exhaustive reference/impact lists and acceptance/security/data-integrity checks with native rg/current source, even when tgrep returned matches. Do not infer completeness from speed, exit 0, an empty result or `Indexing: complete`. Full tests, lint/build output and native review diffs remain authoritative. No automatic re-run of mutating verification commands and no startup/background queue draining.
