## ADDED Requirements

### Requirement: Reinstall retires previously owned assets
A reinstall SHALL retire the extension files, the saved tool state, the published source copies and the pinned runtime left by an earlier install, and SHALL preserve any asset it cannot prove this project wrote.

#### Scenario: Owned assets are retired
- **WHEN** an earlier install left receipt-owned extension files, a saved state entry, published source copies matching the recorded digests and a runtime whose ownership marker names the project
- **THEN** a reinstall removes the receipted files and the state entry, moves the runtime into the private backups area, and leaves every unrelated file, state key and extension in place

#### Scenario: Unowned data is preserved
- **WHEN** an operator-written file occupies a retired path, or a symlink, regular file or unmarked directory occupies the runtime path
- **THEN** the install fails closed naming the preserved path, no bytes are deleted, and the rest of the transaction rolls back

#### Scenario: Move failure cannot publish partial Pi policy
- **WHEN** moving an owned runtime into backups fails
- **THEN** direct Pi wiring leaves the runtime directory, policy, receipt and state unchanged

#### Scenario: Journaled installation fails after wiring
- **WHEN** the installer transaction fails a late verification after source publication and Pi wiring
- **THEN** its journal restores owned files and the original runtime remains in place

#### Scenario: Source publication retires owned copies
- **WHEN** source publication runs
- **THEN** retired published copies are removed by the receipt-aware Plan without touching unowned copies

#### Scenario: Completed Pi wiring retires all owned assets
- **WHEN** direct Pi wiring or the wiring-only installer transaction succeeds
- **THEN** owned published copies, Pi extension files, saved state and the runtime are retired without deleting unowned assets; the runtime moves only after all outer installer phases succeed
