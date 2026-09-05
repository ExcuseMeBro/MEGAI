# Verification — Ix retirement

Asana: 1218203901058317. Approved scope: free codedb + zvec-grep + native read/edit, rg fallback; no muonry/CodeDB Pro. No new dependency or remote embedding/provider route.

| Requirement | Implementation / evidence | Result / gap |
| --- | --- | --- |
| Ix is not an active tool | `bin/megai`, `lib/main.sh`, Pi/OMP skills, removed installer and safety patch; `python3 tests/ix-retirement.py`, `bash -n bin/megai lib/main.sh`, `git diff --check` | PASS: no active Ix paths, 17 contiguous installer stages. Only explicit retirement docs/helper/tests and historical spec records mention Ix. |
| Safe explicit retirement | `lib/retire_ix.py`; 9 offline tests cover preview, mixed hook/config preservation, private recoverable backups, idempotence, malformed data, symlinks, custom files/Windows commands/marketplaces and ambiguous TOML | PASS. Exact known SHA-256 fingerprints verified against shipped 2a616ee and installed legacy files. Unknown versions/custom registrations remain manual. |
| Preserved free search stack | Before/after `bash tests/mcp-wiring.sh`, `bash tests/zvec-grep-integration.sh`, `bash tests/pi-task-flow.sh`; after `bash tests/omp-integration.sh`, `bash tests/orchestration-policy.sh` | PASS. Existing coding/MCP wiring unchanged. |
| Current-host runtime cleanup | Explicit helper applied 10 changes; second apply 0. Archived only source-matching hooks/MCP, Ix-only plugins/data, standalone runtime and launcher. Verified Homebrew formula then `HOMEBREW_NO_AUTOREMOVE=1 HOMEBREW_NO_AUTO_UPDATE=1 brew uninstall ix`. Docker stop/rm used only two freshly identity-checked IDs, never volume flags. | PASS: no Ix launcher or active registrations; all unrelated container IDs and every Docker volume unchanged. Homebrew Node dependencies retained. No arbitrary project scan. |
| Observable local tools | `codedb --version` 0.2.56, `zg --version` 0.2.1, `rg --version` 15.2.0; `codedb outline lib/retire_ix.py` returns structural results. Existing primary zvec index refreshed with explicit `local/potion-code-16m-v2`; `zg query 'global Pi MCP configuration'` returns relevant README/wiring hits. | PASS, actual query results observed. No performance improvement claimed. |
| Planning contract | `OPENSPEC_TELEMETRY=0 openspec validate remove-ix --type change --strict --no-interactive` | PASS; not a substitute for tests. |

## Independent review

Paseo Pi/Sol high reviewer `8c385ea3-9735-487f-9dd6-411321f3fed6`, one launch reused for bounded refinements, final PASS. Fixed two findings: replaced weak header ownership matching with exact file hashes; added custom-marketplace diagnostics. Added the identified Homebrew retirement documentation gap. Reviewer verified live hook transformation in memory preserves all five Paseo and four Muxy hooks while removing all five Ix hooks.

## Local artifacts and remaining limits

- Config restore manifest: `~/.megai/backups/ix-retirement/run-a529rxwm/manifest.json`.
- Runtime/deployment/Homebrew archive: `~/.megai/backups/ix-retirement/host-JaAWUKaf/`, with `runtime-manifest.json`. Private backups include recoverable data; keep outside MEGAI if uninstalling MEGAI later.
- Logs retained locally: `/tmp/megai-remove-ix-final-tests.log`, `/tmp/megai-remove-ix-verification.log`, `/tmp/megai-codedb-proof.log`, `/tmp/megai-zvec-query-proof.log`, `/tmp/megai-post-ix-doctor.log`.
- Deployment correction: copying repository files initially removed the installed CLI executable bit. Restored original installed modes from backup, then reran the actual doctor command successfully. No source installer change needed: normal installation already chmods shell files.
- Doctor confirms codedb and global Pi zvec MCP, and does not reference Ix. It also reports unrelated agent-memory unavailability, missing OMP and incomplete specialist skill links; these were not repaired under this scope.
- Old agent sessions may cache removed hooks/skills: reopen them. Historical plugin usage, Docker volumes and recovery archives are intentionally retained, not active integrations. Customized/project-local Ix installations outside the MEGAI/global paths were not recursively searched or changed.
- Dev delivery and In Review handoff follow the existing lifecycle; main promotion and spec archival remain separately user-approved. Actual delivery URL is recorded at the Asana/.todos handoff.
