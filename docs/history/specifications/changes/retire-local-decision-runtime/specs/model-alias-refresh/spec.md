## ADDED Requirements

### Requirement: Active GPT aliases match the current generation
Every active template, settings file, preset, extension source, test and policy document SHALL name the current `gpt-6-*` aliases, and the previous `gpt-5.6-*` spellings for those roles SHALL be absent from active tracked content. Historical benchmark records, protocols, audits and archived policy examples SHALL retain their original model identities and bytes. Unrelated model generations SHALL keep their own names.

#### Scenario: Aliases are current everywhere
- **WHEN** the frozen acceptance check scans active tracked content for the previous `gpt-5.6-*` alias spellings, excluding the named historical paths
- **THEN** no match remains in active content, and only the intended `gpt-6-*` names were introduced

#### Scenario: Economy preset keeps its role policy
- **WHEN** `python3 -B tests/pi_deepseek_preset.py` runs
- **THEN** the preset installs the reviewer role with `gpt-6-sol`, preserves the operator's native provider/model/thinking settings, and stays idempotent

#### Scenario: Historical records retain their measured model identity
- **WHEN** benchmark results, protocols, audits and archived examples are compared with their base-commit versions
- **THEN** the named historical paths match byte-for-byte in the worktree and index; no completed measurement is relabeled
