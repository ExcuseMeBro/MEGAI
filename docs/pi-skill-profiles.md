# Opt-in Pi skill profiles (native exclusion snippets)

A small, **explicitly opt-in** way to narrow Pi skill discovery for coding, design
or mobile work. It is a read-only snippet generator: it prints native
`settings.json` exclusion entries for the user to merge by hand. Nothing is applied
globally, no file is written, and no installer or hook is added.

> **Not installed yet.** This helper is repository source (`lib/pi_skill_profiles.py`);
the commands below run it from the checkout. It is not copied into `~/.megai` by
this change, and it never edits `settings.json` itself.

## What a profile is

A profile is the exact set of native `skills` exclusion patterns (`!name`) that
narrow known optional global design/mobile skills. Pi's own loader applies them to
auto-discovered user skill directories (`~/.pi/agent/skills` and
`~/.agents/skills`); project selections and package filters keep their own rules.
Core, safety and accessibility (a11y) skills are never listed, and a self-check
rejects any profile that would contain one.

| Profile | Optional skills narrowed |
| --- | --- |
| `coding` | design + mobile optional skills |
| `design` | mobile optional skill |
| `mobile` | design optional skills |

The excluded names are reviewed constants in
[`lib/pi_skill_profiles.py`](../lib/pi_skill_profiles.py); `PROTECTED` is the
guard list (`megai`, `megai-acceptance`, `megai-task-flow`,
`agent-worktree-lifecycle`, `a11y-audit`, `code-review`, `diagnosing-bugs`, `tdd`,
`research`, `grilling`, `writing-for-agents`, and the other core skills).

## Commands

```bash
# List profiles.
python3 lib/pi_skill_profiles.py profiles

# Print the JSON snippet to merge into settings.json. Never writes.
python3 lib/pi_skill_profiles.py snippet coding
# {"skills": ["!appllama-app-design-skill", "!apply-aesthetic", ...]}

# Human-readable summary of what a profile narrows and how to merge/restore.
python3 lib/pi_skill_profiles.py explain coding

# Read-only: which installed skills the profile would narrow.
python3 lib/pi_skill_profiles.py scan coding --skills-dir ~/.pi/agent/skills
```

Merge the snippet into `~/.pi/agent/settings.json` (global) yourself. A profile
does not own the whole file: **snapshot `settings.json` privately, then append
only the exclusions that are not already there, preserving existing entries,
their order and every unrelated setting, and record which entries you added.**
`missing_exclusions` in the generator reports exactly that subset. Existing user
filters are preserved: the generator never rewrites settings, and a project
`.pi/settings.json` or package entry keeps its own scope. Pi trust rules are
unchanged, so an untrusted project still contributes no project skills.

## Restore and exceptions

- **Restore only the entries you added.** If `!design-code` was already in your
  settings before adopting a profile, leave it in place; deleting the emitted
  pattern list would remove a pre-existing user-owned exclusion. Remove only the
  newly appended entries and keep the snapshot as the original.
- Force one narrowed skill back with `+<exact-path>` (native force-include), for
  example `"+/Users/me/.pi/agent/skills/design-code/SKILL.md"`.
- `-<exact-path>` is Pi's exact force-exclude and is not used by these profiles.

## Boundaries

This is discovery narrowing, not a sandbox, permission gate or acceptance change.
It cannot see package skills, CLI `--skill` paths or project selections, and it
makes no token, cost or speed claim. `scan` mirrors the profile names on disk but
the native Pi loader stays authoritative; the regression suite loads the real
`DefaultResourceLoader` against disposable fixtures to prove core/safety/a11y
skills survive, optional skills are removed and re-included, and project
selection/trust is honored.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/skill_profiles.py
```

Runs the generator unit checks plus the native-loader fixture regression (skipped
only when the installed Pi package or Node is unavailable).
