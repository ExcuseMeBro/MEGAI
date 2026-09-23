## ADDED Requirements

### Requirement: Reinstall retires previously owned assets
A reinstall SHALL retire the extension files, the saved tool state, the published source copies and the pinned runtime left by an earlier install, and SHALL preserve any asset it cannot prove this project wrote.

#### Scenario: Owned assets are retired
- **WHEN** an earlier install left receipt-owned extension files, a saved state entry, published source copies matching the recorded digests and a runtime whose ownership marker names the project
- **THEN** a reinstall removes the receipted files and the state entry, moves the runtime into the private backups area, and leaves every unrelated file, state key and extension in place

#### Scenario: Unowned data is preserved
- **WHEN** an operator-written file occupies a retired path, or a symlink, regular file or unmarked directory occupies the runtime path
- **THEN** the install fails closed naming the preserved path, no bytes are deleted, and the rest of the transaction rolls back

#### Scenario: Non-Git package installs keep working
- **WHEN** `lib/retire_legacy_sources.py` runs during `megai install` or the installer transaction
- **THEN** the retired published copies are staged through the same plan and dry-run check, and its existing manifest validation stays unchanged
