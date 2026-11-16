---
name: ai-design-check
description: >-
  Design rules and a checker for interfaces built with AI agents (dashboards, admin panels, SaaS screens). Use before building or changing any UI screen, component, button, form field, label, menu item, table or chart, and before reviewing UI changes: shared components with one look per element, sentence case, one type and radius scale, one selector language, focus and names for accessibility, locale-aware formatting, no generated-UI tells.
---

# Enmera design rules

Installed from enmerasoftware/ai-design-check at `930e1e966603436073f5e69e0a644fa678b6791e`. Apply these rules when relevant to an approved UI task; existing project design and safety rules take precedence. The pinned checker is `node "$HOME/.pi/agent/skills/ai-design-check/package/bin/ai-design-check.js"` (no `npx`, installer or automatic hook). Scope reads to approved task-owned files; check that input files and directories contain no symlinks to outside the approved scope (the checker follows file symlinks). Do not start a browser or run visual/browser checks during review unless the user explicitly invokes `/rwbrowser` or existing acceptance requires that evidence. Browser-backed `story`/`narrow`, generated files and dependency installs require appropriate task approval; do not restart sessions.

## Before you write UI

1. Read `package/RULES.md` from this skill directory (Turkish: `package/RULES.tr.md`), or run the pinned checker with `rules`.
2. Decide the place first: which menu section, its own row or a tab of an existing page, which URL prefix
   (`menu-by-job`). State the decision in one line before writing code.
3. Reuse the project's components for the selector language: segmented control for the primary choice, plain
   sub-tabs on the same row, pill chips only for filters (`selector-language`).
4. Know the context: an app screen (dashboard, settings, tables) is dense and quiet; a marketing page may use display
   type and more colour. If the project has a DESIGN.md or a brief, it wins over these defaults.
5. Run the pinned checker with `inventory` on the approved project once: it shows the looks that already exist for buttons, inputs,
   headings, badges and cards. Use one of those; do not invent another.

## While you write

- Buttons, inputs, selects, badges and cards come from the shared components. A different look is a new `variant`
  or `size` on the component, never a `className` with colour, radius, padding or height on one instance.
- When the same block of markup appears a third time, extract a component instead of copying it.
- Sentence case for every label you add, in the source language and in each translation; keep proper names.
- Never remove a focus ring without a focus-visible replacement; give icon-only buttons an aria-label.
- Format numbers, dates and money through the project's locale formatter; case changes name the locale (Turkish i/İ).
- Font sizes and radii only from the theme scale; never `text-[Npx]` or a one-off `rounded-[..]`.
- No tracked uppercase labels, emoji as decoration, gradient text, purple gradients, side stripes, decorative glow,
  blurred blobs, fake pulses, marquees, hover growth, or headings at weight 800–900.
- Spacing on the 4 px grid; copy without exclamation marks, greetings as titles or unsourced social proof.
- To clean up a screen that already looks generated, use the `ai-design-fix` skill.
- Wide tables take the full width with the last column absorbing spare width; uneven cards go into a grid masonry.
- Headline numbers say what they are compared with; empty data shows an empty state.

## After you write

Run the checker and fix what it reports. When a rule does not apply, add an inline ignore with the reason
(`ai-design-check-ignore-next-line rule-id -- why`) or a config `allow` entry; never ignore to skip a fix:

```bash
node "$HOME/.pi/agent/skills/ai-design-check/package/bin/ai-design-check.js" path/to/approved/screen
```

For the rules marked *review* (layout, selectors, empty states, contrast), use available screenshots at desktop and phone width. If new browser evidence is needed, follow the project browser/acceptance gate; otherwise report the visual validation gap.

## Adding to the rules

When the user corrects a design decision that is general, propose adding it to `rules.json` of this package
(with `why` and `fix` in English and Turkish) so the next project gets it too.
