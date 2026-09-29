## Why

Ix is no longer wanted in MEGAI. Use the existing free local codedb + zvec-grep tools, native reads/edits and rg fallback without introducing Pro licensing or another service.

Asana: 1218203901058317. The earlier muonry proposal was rejected after upstream inspection showed it is now paid CodeDB Pro.

## What Changes

- **BREAKING**: remove Ix installation/update, status/doctor checks, agent guidance and integration tests for its former installer.
- Provide an explicit, backed-up retirement helper for known legacy Ix registrations and MEGAI-owned leftovers. Preserve unrelated hooks/configuration and fail closed on malformed inputs.
- Retire the current host's Ix runtime after checking ownership; retain database volumes and recoverable backups rather than erase user data.
- Keep codedb, zvec-grep, native file tools and rg working as before.

## Capabilities

### New Capabilities
- `ix-retirement`: stop offering Ix and safely detach existing integration.

### Modified Capabilities
None.

## Impact

`bin/megai`, `lib/main.sh`, former Ix installer/safety patch, a retirement helper, README, Pi/OMP skill guidance and focused tests. No new provider, toolchain, remote indexing, automatic project scan, or changes to other specialist tools. No performance claim without measurements.
