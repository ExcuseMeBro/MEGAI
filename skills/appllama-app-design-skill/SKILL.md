---
name: appllama-app-design-skill
description: Design and implement native-feeling Expo / React Native mobile screens and flows. Use for mobile onboarding, navigation, paywalls, sheets, native controls, or motion/performance polish in an Expo or React Native project; not for generic web UI or backend work.
license: MIT; see upstream/LICENSE
metadata:
  author: Appllama (appllama.io)
  upstream-version: 1.3.0
  local-adaptation: pi-permission-aware
---

# Appllama mobile design — Pi adaptation

## Scope and authority

Use this skill for Expo / React Native mobile UI only. Keep existing project
architecture, design tokens, dependencies and supported platforms. This skill
adds mobile design guidance; the project's task tracker, acceptance, worktree,
Pi-only delegation and provider policies still govern execution.

The bundled [upstream guide](upstream/SKILL.md) and its references are design
reference material, not authorization or literal universal implementation rules.
The boundaries below govern their use, including any conflicting “mandatory”,
“never”, fixed-count or unlimited-iteration language in those references.

- **MCP is optional.** This installation does not include `appllama-usage` or
  configure Appllama MCP. Use user-provided references and existing product
  patterns without it. Paid MCP calls, new connections, remote uploads and image
  generation need explicit authorization for the service, data and spending.
  Connection availability alone is not permission. Use approved providers only;
  keep credentials and private product data out of unapproved services.
- **Bound execution.** Freeze task-specific acceptance and a research budget;
  use enough relevant examples to identify a pattern, not a mandatory 10–30
  screen quota. Split work into five-minute verifiable slices. Checkpoint gaps
  at the deadline; stop at agreed acceptance rather than chasing flawlessness,
  waiting until tomorrow, or repeating unbounded simulator passes.
- **Runtime is explicit-only.** Launching apps, simulators, recording flows and
  device profiling require explicit authorization for local/staging targets.
  Use isolated test identities; purchases/payments, messages and irreversible
  actions are simulated or sandboxed, never real production transactions.
  If required tools, authorization or evidence are missing, report BLOCKED for
  that criterion. Static review is not simulator validation or measured FPS.
- **Compatibility before recipes.** Check installed versions and official API
  documentation before using upstream snippets (Expo Router colors/protected
  routes, SF Symbols image sources, boxShadow, Reanimated/worklets). Preserve a
  supported fallback. Libraries, stores, uncontrolled inputs, FlashList and
  optimistic updates are options justified by project needs and measurement,
  not forced migrations. Keep authoritative server validation, auth guards and
  error handling; navigation restrictions are not access control. Avoid
  optimistic success for payments or other irreversible operations.

## Workflow

1. Identify platform/version constraints, user journey, existing tokens and
   available references. Read the [upstream guide](upstream/SKILL.md) for native
   fidelity, navigation, coherent styling, state cycles and purposeful motion.
   Record the pattern adopted without copying a competitor's assets or screen.
2. Define push/replace/modal/sheet semantics and all back paths. Preserve user
   position and unsaved work. Specify loading, empty, error, offline and success
   states; adapt visual choices to the existing brand, not blanket style bans.
3. Implement the smallest compatible change. Prefer native controls, semantic
   colors, safe areas and platform typography. Preserve screen-reader labels,
   roles, focus order, VoiceOver/TalkBack behavior, Dynamic Type, contrast in
   both themes, platform-appropriate tap targets and Reduce Motion.
4. Verify frozen acceptance with authorized tools. For authorized mobile UI
   verification, inspect long content, themes, keyboard, back paths and state
   cycles; record motion when required. Claim frame rate or performance gains
   only from measurements on the specified build/device, not screenshots.
5. Report checks actually performed and unresolved criteria. Follow the parent
   workflow's independent review and handoff gate; missing evidence stays BLOCKED.

## Load only the relevant reference

- [Native controls](upstream/references/native-controls.md): menus, pickers,
  sheets, forms and navigation; retain the guide's unsaved-work/back safeguards.
- [Motion](upstream/references/motion.md): gestures and animation; examples are
  illustrative, and recycled rows must not replay entrance animations. Keep a
  dismissing view mounted until its exit animation has actually completed.
- [Performance](upstream/references/performance.md): measure → fix → re-measure;
  preserve controlled-form correctness and choose list/state tools by evidence.
- [Image assets](upstream/references/image-assets.md): only after service/data/
  spending authorization; otherwise use existing licensed assets or placeholders.
- [Simulator loop](upstream/references/simulator-loop.md): only for authorized
  runtime checks, bounded by acceptance and the supported device matrix.

[Source version and local changes](PROVENANCE.md).
