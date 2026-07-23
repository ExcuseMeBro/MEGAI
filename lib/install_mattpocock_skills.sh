#!/usr/bin/env bash
# Matt Pocock's promoted engineering/productivity skills for Claude Code, Codex, and Pi.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"

command -v npx >/dev/null 2>&1 || { warn "npx not found — Matt Pocock skills skipped"; exit 0; }

skills=(
  ask-matt
  code-review
  codebase-design
  diagnosing-bugs
  domain-modeling
  grill-with-docs
  implement
  improve-codebase-architecture
  prototype
  research
  resolving-merge-conflicts
  setup-matt-pocock-skills
  tdd
  to-spec
  to-tickets
  triage
  wayfinder
  grill-me
  grilling
  handoff
  teach
  writing-great-skills
)

npx --yes skills@latest add mattpocock/skills \
  --global \
  --agent claude-code codex pi \
  --skill "${skills[@]}" \
  --yes

ok "Matt Pocock skills installed globally (${#skills[@]} promoted skills, 3 agents)"
