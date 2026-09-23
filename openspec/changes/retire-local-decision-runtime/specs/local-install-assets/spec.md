## ADDED Requirements

### Requirement: No tracked Claude Code plugin enablement
The repository SHALL NOT track `.claude/settings.json` or any other repository-local Claude Code plugin enablement for this stack. Agent references to other harnesses SHALL resolve against their own configuration roots.

#### Scenario: Repo-local Claude settings stay absent
- **WHEN** the tracked tree is listed
- **THEN** `.claude/settings.json` is absent and Git history still holds the removed file

#### Scenario: Remaining Claude references are harness-scoped
- **WHEN** the remaining Claude references in installer scripts, tests and generic documentation are read
- **THEN** they resolve against `$HOME/.claude` or another user-owned configuration root, and no source file reads a repository-local `.claude` path

#### Scenario: History and other checkouts are untouched
- **WHEN** the removal lands
- **THEN** no Git history is rewritten and no filesystem path outside this tracked repository is modified
