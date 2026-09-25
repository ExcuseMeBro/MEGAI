## 1. Reproduce and protect native routing

- [x] 1.1 Add offline regressions for the GPT Sol high / DeepSeek Flash high / GPT Astra high roles, Agy removal and one-way DeepSeek balance → Luna high fallback; capture assertion-specific failing output before implementation.
- [x] 1.2 Preserve existing negative auth/permission/second-failure tests and demonstrate the focused tests pass after changes.

## 2. Restore the managed Pi profile

- [x] 2.1 Remove Agy-specific extension, preset and mandatory guidance via the ownership-aware installer; verify no active Agy tool is loaded and no unowned data is changed.
- [x] 2.2 Add explicit native GPT/DeepSeek role preset and installable DeepSeek → Luna fallback with `high` thinking on transition; verify focused role, installer and fallback tests.
- [x] 2.3 Update relevant documentation and OpenSpec task marks; verify `openspec validate restore-native-pi-routing --strict` and changed-Python Ruff.

## 3. Review and delivery

- [ ] 3.1 Capture committed exact-SHA checks and independent GPT Astra security review; verify every acceptance criterion against the source-current diff.
- [ ] 3.2 Preview and safely apply only owned runtime configuration with private backup, confirm fresh-session routing; deliver to local dev only with a valid queue reservation, otherwise report the exact hold.
