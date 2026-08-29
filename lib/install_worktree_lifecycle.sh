#!/usr/bin/env bash
# Install the safe dev-merge/worktree-cleanup skill and always-on policy for
# Claude Code, Codex, Pi, and Oh My Pi.
set -euo pipefail

MEGAI_HOME="${MEGAI_HOME:-$HOME/.megai}"
# shellcheck source=ui.sh
. "$MEGAI_HOME/lib/ui.sh"
# shellcheck source=state.sh
. "$MEGAI_HOME/lib/state.sh"

SOURCE="$MEGAI_HOME/skills/agent-worktree-lifecycle/SKILL.md"
ORCHESTRATOR_SOURCE="$MEGAI_HOME/skills/smart-development-orchestrator/SKILL.md"
MODE="${1:-install}"
BEGIN='<!-- megai:worktree-lifecycle:begin -->'
END='<!-- megai:worktree-lifecycle:end -->'

policy_body() {
  cat <<'EOF'
<!-- megai:worktree-lifecycle:begin -->
# Agent branch and worktree lifecycle
- Default primary development and integration to `dev`; run `megai dev` from a clean `main`/`master` checkout.
- When work has two or more independent implementation slices, the parent defines non-overlapping ownership and remains the sole integration owner.
- Use the `smart-development-orchestrator` skill for writer workspace creation, model routing, integration, and cleanup.
- Inside Paseo, read-only workers use same-workspace agent tabs. Every writer MUST be launched by `create_workspace` with worktree isolation and a `task/<slug>` branch from `dev`, followed by `create_agent` with the returned `workspaceId`; never run concurrent writers in the parent workspace.
- Outside Paseo, registered OMP/Git worktrees may provide equivalent isolation. Native OMP task isolation is not a substitute for a visible Paseo writer workspace when Paseo is available.
- After focused verification and review, merge each successful task branch into `dev`; never apply concurrent agent writes directly to the primary checkout.
- At ship, run `megai finish --verified --target dev`: push verified `dev`, reuse the one open `dev` → `main` PR/MR, and clean only the merged task worktree/branch.
- Complete the task after dev delivery and cleanup, then ask the user whether to promote `dev` to `main`. Only after an explicit affirmative answer run `megai promote --approved`; it merges the reviewed request, synchronizes main, and preserves dev. Never infer approval or enable deferred auto-merge.
- After dev delivery, orchestrators call `archive_workspace` only for successfully merged worker workspaces. Never archive the primary `dev` workspace or dirty/unmerged/failed work. Stop on missing `dev`/`main`/`origin`, dirty state, failed verification, conflicts, forge/auth/push/request/promotion failures, or ambiguous ownership.
<!-- megai:worktree-lifecycle:end -->
EOF
}

validate_policy() {
  local file="$1"
  [ -f "$file" ] || return 0
  awk -v begin="$BEGIN" -v end="$END" '
    $0 == begin { if (open) bad=1; open=1; next }
    $0 == end { if (!open) bad=1; open=0; next }
    END { if (open || bad) exit 1 }
  ' "$file"
}

remove_policy() {
  local file="$1" tmp
  [ -f "$file" ] || return 0
  validate_policy "$file" || { warn "worktree lifecycle: malformed markers; unchanged: $file"; return 1; }
  tmp="$(mktemp "${file}.XXXXXX")"
  awk -v begin="$BEGIN" -v end="$END" '
    $0 == begin { skip=1; next }
    skip && $0 == end { skip=0; next }
    !skip { print }
  ' "$file" >"$tmp"
  if grep -q '[^[:space:]]' "$tmp"; then
    mv "$tmp" "$file"
  else
    rm -f "$tmp" "$file"
  fi
}

install_policy() {
  local file="$1" tmp
  mkdir -p "$(dirname "$file")"
  [ -f "$file" ] || : >"$file"
  validate_policy "$file" || { warn "worktree lifecycle: malformed markers; unchanged: $file"; return 1; }
  tmp="$(mktemp "${file}.XXXXXX")"
  awk -v begin="$BEGIN" -v end="$END" '
    $0 == begin { skip=1; next }
    skip && $0 == end { skip=0; next }
    !skip { print }
  ' "$file" >"$tmp"
  if grep -q '[^[:space:]]' "$tmp"; then printf '\n' >>"$tmp"; fi
  policy_body >>"$tmp"
  mv "$tmp" "$file"
}

is_managed_skill() {
  local source="$1" dest="$2" legacy
  [ -f "$dest" ] || return 1
  grep -Fxq 'managed-by: megai' "$dest" && return 0
  [ -f "$source" ] || return 1
  legacy="$(mktemp)"
  awk '$0 != "managed-by: megai"' "$source" >"$legacy"
  if cmp -s "$legacy" "$dest"; then
    rm -f "$legacy"
    return 0
  fi
  rm -f "$legacy"
  return 1
}

install_managed_skill() {
  local source="$1" dir="$2" dest="$2/SKILL.md"
  if [ -e "$dest" ] && ! is_managed_skill "$source" "$dest"; then
    warn "worktree lifecycle: preserving user-owned skill collision: $dest"
    return 0
  fi
  mkdir -p "$dir"
  cp "$source" "$dest"
}

remove_managed_skill() {
  local source="$1" dir="$2" dest="$2/SKILL.md"
  [ -e "$dest" ] || return 0
  if ! is_managed_skill "$source" "$dest"; then
    warn "worktree lifecycle: preserving user-owned skill: $dest"
    return 0
  fi
  rm -f "$dest"
  rmdir "$dir" 2>/dev/null || true
}

skill_roots=(
  "$HOME/.agents/skills"
  "$HOME/.claude/skills"
  "$HOME/.pi/agent/skills"
  "$HOME/.omp/agent/skills"
)
policy_files=(
  "$HOME/.codex/AGENTS.md"
  "$HOME/.pi/agent/AGENTS.md"
  "$HOME/.claude/CLAUDE.md"
  "$HOME/.omp/agent/RULES.md"
)

if [ -d "$HOME/.omp/profiles" ]; then
  for agent_dir in "$HOME/.omp/profiles/"*/agent; do
    [ -d "$agent_dir" ] || continue
    skill_roots+=("$agent_dir/skills")
    policy_files+=("$agent_dir/RULES.md")
  done
fi

if [ "$MODE" = "--remove" ]; then
  for root in "${skill_roots[@]}"; do
    remove_managed_skill "$SOURCE" "$root/agent-worktree-lifecycle"
    remove_managed_skill "$ORCHESTRATOR_SOURCE" "$root/smart-development-orchestrator"
  done
  for file in "${policy_files[@]}"; do
    remove_policy "$file"
  done
  ok "worktree lifecycle: global skills and managed policies removed"
  exit 0
fi

[ -f "$SOURCE" ] || { warn "worktree lifecycle skill missing: $SOURCE"; exit 0; }
[ -f "$ORCHESTRATOR_SOURCE" ] || { warn "smart orchestrator skill missing: $ORCHESTRATOR_SOURCE"; exit 0; }
mkdir -p "$MEGAI_HOME/backups"
for root in "${skill_roots[@]}"; do
  install_managed_skill "$SOURCE" "$root/agent-worktree-lifecycle"
  install_managed_skill "$ORCHESTRATOR_SOURCE" "$root/smart-development-orchestrator"
done
for file in "${policy_files[@]}"; do
  backup_key="$(printf '%s' "$file" | cksum | awk '{print $1}')"
  [ ! -f "$file" ] || cp "$file" "$MEGAI_HOME/backups/$(basename "$file").${backup_key}.worktree.$(date +%s).bak" 2>/dev/null || true
  install_policy "$file"
done

state_set '.tools["worktree-lifecycle"]' "{\"skill\":\"$SOURCE\",\"wired\":true}"
state_set '.tools["smart-development-orchestrator"]' "{\"skill\":\"$ORCHESTRATOR_SOURCE\",\"wired\":true}"
ok "worktree lifecycle and smart orchestrator: installed globally for Claude Code, Codex, Pi, and OMP"
