# Opt-in Pi token profile

A compact, **explicitly opt-in** profile that reduces ceremony and chat tokens
without changing Pi's ordinary defaults. Nothing here is active until the user runs
`--apply`; `--remove` returns the baseline.

## What it installs

| Asset | Purpose |
| --- | --- |
| `~/.pi/agent/AGENTS.md` marker block `megai:token-profile:begin/end` | Always-loaded pointer to the profile and its safety overrides |
| `~/.pi/agent/skills/caveman/{SKILL.md,LICENSE.md}` | Compact chat-prose core (MIT, attributed) |
| `~/.pi/agent/skills/ponytail/{SKILL.md,LICENSE.md}` | Minimal-solution core (MIT, attributed) |
| `~/.pi/agent/megai-token-profile.json` | Sidecar `{"schema":1,"profile":"max"}` read by the Headroom adapter |
| `~/.pi/agent/extensions/megai-headroom/index.ts` | Existing adapter, refreshed so the sidecar is honored |

No shared `~/.agents` writes, no `settings.json` overrides, no shell edits, no
provider/router/telemetry calls, no upstream installer. `LICENSE.md` is not a skill;
Pi discovery reads only `SKILL.md` inside each skill directory.

## Commands

```bash
# Preflight only (default). Never writes. Exit 0 only when RTK and the selected
# cores are usable; otherwise prints a BLOCKED line and exits nonzero.
python3 ~/.megai/lib/pi_token_profile.py --check

# Deliberate apply: requires an existing RTK binary.
RTK_BIN=/opt/homebrew/bin/rtk python3 ~/.megai/lib/pi_token_profile.py --apply

# Fail unless the installed profile matches source and activation is complete.
python3 ~/.megai/lib/pi_token_profile.py --verify

# Remove only receipt-owned assets; leaves settings, auth, models and user text.
python3 ~/.megai/lib/pi_token_profile.py --remove
```

`--apply` prints `installed-with-gap` and a bounded explanation when a user
filter excludes an installed core: the files are owned and current, but the
profile is not fully activated, and `--verify` then exits nonzero (`BLOCKED`).

When settings.json is unreadable, not a JSON object, or its `skills` entry is not
a list, the profile reports that activation could not be checked instead of
crashing or writing settings. Explicit positive skill paths are additive in Pi and
are never treated as an allow-list; only an exclusion (`!`/`-`) that matches an
installed core is reported as a gap. The native Pi loader remains authoritative.

The installer reuses the existing `lib/slim_wiring.py` `Plan`: ownership receipts,
preflight-before-write, concurrent-drift refusal and private backups. Re-apply is
idempotent. Malformed, reversed or duplicated markers, unowned changed assets and
symlinked destinations fail closed without any write. Missing RTK blocks `--apply`
rather than guessing or downloading a source.

`stage_profile(plan, root, source, remove=False)` is the public staging seam. It
stages the marker, cores and sidecar into a caller-owned `Plan` **without applying**,
so canonical `~/.megai` source publication, the matching Headroom adapter and the
sidecar can land in one atomic transaction.

## Headroom under `profile: max`

Caveman owns chat terseness, so the adapter stops injecting Headroom's duplicate
concise-output steering at `session_start`. Only that steering is suppressed:

- `MEGAI_HEADROOM=0`, compression, `headroom_retrieve`, local memory and the stable
  native prefix are unchanged.
- An explicit `MEGAI_HEADROOM_VERBOSITY` and `/headroom-verbosity N` always win over
  the profile.
- `normal mode` stops terse style, not evidence or compression.
- A missing sidecar leaves the current default untouched; an invalid sidecar emits
  one bounded warning and keeps the safe baseline without throwing.

The sidecar stores no session data.

## RTK policy

RTK is used only through the existing `bash` tool, for optional large read-only
discovery: `rtk ls`, `rtk git status`, `rtk git log`, always with
`RTK_TELEMETRY_DISABLED=1`. No `rtk init`/`trust`, and no `rtk read/test/diff` or any
mutation. Exact and absence decisions, raw tests, errors, diffs and source use native
`rg`/`read`/`git`. RTK output is never re-filtered through Headroom, and no claim is
made that Headroom can retrieve a pre-RTK original.

## Accuracy and safety over terseness

Both cores are rewrites, not copies. They keep negations, numbers and units, exact
code and error strings, the user's language, genuine uncertainty and requested
detail; security warnings and irreversible-action confirmations use normal prose;
persisted artifacts stay normal prose; and the MEGAI three-step flow plus every
approval/acceptance gate is unchanged. No universal percentage saving is claimed —
any measurement is reported only for the fixture that produced it.

See [`pi-skill/token-profile/PROVENANCE.md`](../pi-skill/token-profile/PROVENANCE.md)
for exact source pins, hashes and adaptation notes.

## Wiring and activation compatibility

Broad Pi wiring recognizes an **owned valid max profile** and refreshes its marker
and cores from source instead of retiring them as legacy; the `LICENSE.md` filename
matches the convention that wiring already tolerates. The exception is narrow:

- Default wiring without a valid, receipt-owned sidecar is unchanged.
- Unowned, modified or companion files still block, and existing legacy retirement
  still applies to any caveman/legacy resource outside the exact owned core paths.
- Removal removes only owned profile assets; user files remain.

The Headroom activation verifier (`lib/verify_headroom_activation.mjs`) exempts a
local caveman/ponytail core only when the sidecar is valid and the per-file receipts
match the loaded files. A foreign or shared caveman skill, or an unowned/modified
local core, still fails verification.

## Verification

```bash
env PI_PACKAGE_ROOT=<installed pi-coding-agent> RTK_BIN=<rtk> bash tests/pi-token-profile.sh
```

Runs the installer acceptance in a disposable HOME, the real native Pi loader/hooks
(profile present/missing/malformed, overrides, raw messages, RTK bypass, single core
discovery, owned-profile activation vs foreign legacy), the existing Headroom
adapter suite that keeps raw tests, errors, reads, diffs and mutations uncompressed,
and the actual RTK binary on a same-directory listing fixture. Bytes and elapsed
time printed there are sample-only, not token/bill/speed estimates.
