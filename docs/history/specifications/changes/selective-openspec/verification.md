# Verification — selective OpenSpec integration

Asana: 1218202555904869. Agent handoff target: In Review, completed=false. User explicitly requested README refresh and promotion of current changes to main on 2026-09-05; promotion still requires successful verification and dev delivery. OpenSpec archive remains separately unauthorized; this change stays active.

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| Selective planning | `skills/megai-openspec/SKILL.md` selection/prepare sections; optional installer outside `lib/main.sh` | Policy/diff inspection; installer test confirms no project initialization; real CLI context injection passes; `tests/openspec-policy.sh` protects small-fix bypass with a negative mutation |
| Single task identity and checklist | Skill parent boundary; proposal GID; `.todos` summary links to this directory | Static inspection and independently negative-mutated checklist/tracker clauses in `tests/openspec-policy.sh`; only this change's `tasks.md` has the detailed implementation checklist |
| Evidence before handoff | Skill verification/handoff; `openspec/config.yaml` operation guidance | `bash tests/openspec-contract.sh`: valid delta accepted, missing-scenario delta rejected, planning complete despite unchecked implementation tasks; apply/archive/specs guidance observed in real 1.12.0 CLI JSON |
| Optional privacy-preserving installation | `lib/install_openspec.sh`; `bin/megai` uninstall hook | `bash tests/openspec-integration.sh`: fresh/repeated install, exact pin/ignore-scripts flags, telemetry disabled, version mismatch and user-directory/dangling-link collisions rejected, safe removal, multi-location/custom-path registration, ownership replacement, state-key deletion and project preservation |

## Additional checks

- `bash -n lib/install_openspec.sh tests/openspec-integration.sh tests/openspec-contract.sh bin/megai` passed.
- `bash tests/pi-task-flow.sh`, `bash tests/orchestration-policy.sh` and `bash tests/worktree-lifecycle.sh` passed.
- `bash tests/openspec-policy.sh` passed eight policy guardrails and their negative mutations.
- Red/green: strengthened removal test failed against the original installer, then passed after the lifecycle correction.
- `git diff --check` passed.
- Actual OpenSpec 1.12.0 installed; upstream global telemetry setting reads `false`.
- Installed global Pi skill and installer match worktree sources (`cmp`). No other repository was initialized; the default install pipeline and model/provider settings are unchanged.
- Independent read-only Sol review found custom-destination cleanup, runtime version guarding, state-key deletion and policy-test gaps. Parent accepted and fixed these findings. Focused re-review confirmed the lifecycle/version fixes; its remaining stale main-authorization record was corrected in the opening paragraph and checked by the parent. No substantive findings remain unresolved. The original bookkeeping observation preceded completion; all implementation items are now backed by evidence.

## Limits and recovery

Policy/context checks are not proof that every future model turn will comply. OpenSpec operation guidance is advisory, and its CLI does not enforce MEGAI's Asana, approval, test or release gates. The parent retains those responsibilities. No runtime speedup or flawless implementation claim; real-task pilot evidence is still required, with this rollout labelled as a configuration intervention.

The installer was tested with the pinned version, not arbitrary future versions. No full suite or live application test was needed for this CLI/policy change. Remove the owned global bridge with `bash "$HOME/.megai/lib/install_openspec.sh" --remove`; keep the CLI and specs unless their removal is separately requested. State backup: `~/.megai/backups/openspec-20260905/state.json`.
