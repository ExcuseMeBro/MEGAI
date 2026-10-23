# Shipped UI skills

Five curated design-engineering skills live in `pi-defaults/skills/<name>/SKILL.md`.
They are vendored verbatim from the [ui-skills.com](https://www.ui-skills.com/) registry
(fetched 2026-10-23) instead of being linked from `~/.agents/skills`, because links from
third-party kits drifted, duplicated names and ended up suppressed by
`disable-model-invocation: true` — the model could not see them at all.

| Directory | Upstream slug | Purpose |
| --- | --- | --- |
| `frontend-design` | `anthropics/frontend-design` | visual direction, typography, non-templated choices for new UI |
| `interface-design` | `dammyjay93/interface-design` | craft for dashboards, admin panels, SaaS, settings and data UI |
| `baseline-ui` | `ibelick/baseline-ui` | fast deslop pass: spacing, hierarchy, type, layout |
| `make-interfaces-feel-better` | `jakubkrehel/make-interfaces-feel-better` | polish details: hover, shadows, borders, icons, micro-interactions |
| `fixing-accessibility` | `ibelick/fixing-accessibility` | ARIA, keyboard, focus, contrast, form errors |

## Why these five

They are disjoint: build (`frontend-design`), product surface (`interface-design`),
fast cleanup (`baseline-ui`), detail polish (`make-interfaces-feel-better`), and
accessibility (`fixing-accessibility`). The registry holds ~400 more; broad
"run every skill" routers and kit bundles were rejected as redundant, and skills
that need an external engine (accessibility scans, Figma bridges) were rejected
because they cannot run inside Pi.

## Install-time behaviour

`install.py` copies `pi-defaults/skills` into `~/.pi/agent/skills` and
`profile_settings()` adds `+skills/<name>/SKILL.md` for every entry in `UI_SKILLS`.
The explicit include is required: an operator settings file may contain `!**`,
which otherwise hides every copied skill. `verify.mjs` lists the same names in
`requiredSkills`, so a profile that loses one fails verification instead of
silently going quiet.

## Refreshing

```sh
npx ui-skills get anthropics/frontend-design > /tmp/fd.md   # same slugs as the table
```

Review the diff, then replace the matching `SKILL.md`, keep this table current and
re-run `python3 -m unittest tests.pi_defaults`. Do not add a skill here without
also adding it to `install.py:UI_SKILLS` and `verify.mjs:requiredSkills`.
`frontend-design` keeps Anthropic's upstream licence reference; only `SKILL.md` is
vendored.
