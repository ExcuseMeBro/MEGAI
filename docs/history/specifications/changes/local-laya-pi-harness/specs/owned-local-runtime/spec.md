## Purpose

Install and retire the optional on-device Laya Pi inference runtime with provable ownership so operator configuration and the previous Jev implementation remain recoverable.

## ADDED Requirements

### Requirement: Owned Laya installation
The Pi policy installer SHALL provision a pinned, isolated local Laya runtime and stage its Pi extensions using existing ownership receipts and private backups. It SHALL NOT change Pi's selected provider, chat model or thinking level; startup SHALL NOT contact an external decision API or start an unattended daemon.

#### Scenario: First install in an owned clean profile
- **WHEN** a trusted local profile is installed with the Laya policy
- **THEN** the local runtime and Pi extensions are available with recorded ownership, and an offline local inference request succeeds

#### Scenario: Missing or unowned runtime
- **WHEN** a required local runtime or its ownership cannot be verified
- **THEN** installation fails without overwriting the foreign path or claiming the Pi profile is switched

### Requirement: Recoverable Jev retirement
The installer SHALL retire only previously receipt-owned Jev extension and browser skill assets. It SHALL retain Jev source at the separately verified local backup branch tip and preserve credentials, session files, caches, unrelated extensions and operator-edited configuration. Rollback SHALL be possible from that branch and private backup without force deletion or a remote push.

#### Scenario: Owned prior Jev assets
- **WHEN** a prior profile contains matching receipt-owned Jev assets
- **THEN** migration stages their retirement and the new local assets without deleting unrelated files

#### Scenario: Operator-edited Jev asset
- **WHEN** a Jev asset differs from the recorded installed bytes or ownership is absent
- **THEN** migration reports a conflict and preserves that file unchanged

### Requirement: Session-scoped local inference process
The local inference process SHALL start only on demand after Pi session startup, communicate through local private IPC without a public listener, bound each request and response, and close on session shutdown or pipe EOF. A failure SHALL not invoke a hosted Jev fallback or leave a tool call blocked indefinitely.

#### Scenario: Runtime crash
- **WHEN** the local inference process exits unexpectedly during a request
- **THEN** the caller receives a bounded failure, Pi's native safety behavior remains intact and no remote Jev request is made
