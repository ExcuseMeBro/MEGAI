# One-off Asana import checkpoint

`lib/asana_plane_import.py` is retained source from the historical migration branch, not a supported MEGAI command or an active tracker integration. It is not wired into the CLI, installer, Pi, or Codex. Plane remains the sole coordination authority. No live migration is part of branch consolidation.

## Safety and verification boundaries

- Resume must re-prove project privacy before sending source content, including legacy ledgers.
- Established state and label fingerprints reject destination drift. Attachment resume re-reads destination identity, metadata and bytes/checksum; comment resume rechecks owned content.
- Import readbacks are **not** independent preservation proof. `full_verification` and `full_account_parity` remain false.
- `verify` currently checks core identities/privacy only. It reports `status: partial`, identifies unchecked detail categories and returns exit code 2, even if the source manifest is complete and pending queues are empty. Do not treat this as migration acceptance.
- Full source/destination coverage, definitions, comments and attachments/checksums still require a complete independent verification implementation before historical parity can be claimed. Plane API compatibility is fake-tested, not live-verified.
- Keep export data, ledgers and credentials outside Git in private storage. Preserving this source does not authorize running it against live accounts.

Offline regression gates:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q -p no:cacheprovider tests/test_asana_plane_import.py tests/test_asana_plane_import_regressions.py
ruff check --no-cache lib/asana_plane_import.py tests/test_asana_plane_import*.py
```
