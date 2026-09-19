# jevcache (optional CLI)

[jevcache](https://github.com/hyperspaceai/jevcache) is a memoization layer for
Jev-class decisions: an answer is keyed by
`sha256(model ⊕ schema ⊕ canonical(redact(state)))` and a hit returns in ~0 ms, so the
same decision is never billed twice. `lib/install_jevcache.sh` installs it pinned into
`~/.megai/bin/jevcache`:

| | |
| --- | --- |
| version | `v0.1.0`, published 2026-09-19 |
| artefact | one static Rust binary, 2.3–3.2 MB; this repository is distribution only, the source is closed |
| verification | SHA-256 pinned per platform as a literal in the installer, copied from the release's own `.sha256` assets when `v0.1.0` was adopted; nothing is fetched at install time |
| platforms | macOS and Linux, arm64 and x64 |
| on failure | warns and exits 0, so a missing binary never breaks a profile install |

Only `demo`, `decide`, `recall`, `serve`, `stats` and `replay` are used here. The
`publish --remote`, `use`, `market`, `wallet`, `earnings` and `deposit` commands reach the
hosted index and a money surface; nothing in this stack calls them.

## Not wired into the Jev gate

The gate in `pi-skill/jev/index.ts` decides whether a tool call runs as written. jevcache
stays out of that path, deliberately:

- **The traffic does not repeat.** A gate state is the session goal, the working
  directory and the exact call. Two calls that differ by one argument are two keys, so a
  cache would mostly store single-use entries and pay for a dependency it never uses.
- **A hit is not evidence.** The `0.65` objection threshold is a sample of 213 real tool
  calls. Serving a repeat from a cache removes exactly the calls a retune would want to
  sample again, so the number would slowly stop describing the traffic it governs.
- **It would displace the contract.** The gate owns a 5 s deadline, one attempt per
  failure and fail-open on anything it cannot read. Another process on that path adds a
  failure mode without adding a judgment.
- **Age and surface.** `v0.1.0` shipped the day this was written, the binary is closed
  source, and the schema files it reads are documented only in its own README. A path
  that can block a destructive tool call is the wrong place to amortize that risk.

## What it is good for

- Deterministic CI replay of a fixed probe set: `decide` once, `replay` after.
- Sharing one cache between machines: `publish`, then `add` on the other side.
- `jevcache serve` as a standalone HTTP memo (`POST /decide {schema, state}`) for an
  application whose decisions genuinely repeat.

```bash
jevcache demo                       # no key, no schema, no setup
jevcache stats                      # hit rate and spend avoided
JEVCACHE_BACKEND=jev TYPESAFE_API_KEY=… jevcache decide --schema support.route --state ticket.json
```

Revisit the decision above when a caller with real repeats exists. The hand-run probes
under `~/.megai/evidence/` are the closest candidate: re-running one sends the same state
twice, which is exactly what a cache is for.
