#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"
export PATH="$TMP/bin:$PATH"
export GH_LOG="$TMP/gh.log"
export GLAB_LOG="$TMP/glab.log"
cat >"$TMP/bin/gh" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$GH_LOG"
case "${1:-} ${2:-}" in
  'pr list') [ -z "${GH_EXISTING_URL:-}" ] || printf '%s\n' "$GH_EXISTING_URL" ;;
  'pr create') [ -z "${GH_FAIL_CREATE:-}" ] || exit 1; printf '%s\n' 'https://github.example/pull/1' ;;
  *) exit 1 ;;
esac
SH
cat >"$TMP/bin/glab" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$*" >>"$GLAB_LOG"
case "${1:-} ${2:-}" in
  'mr list') [ -z "${GLAB_EXISTING_URL:-}" ] || printf '%s\n' "$GLAB_EXISTING_URL" ;;
  'mr create') printf '%s\n' 'https://gitlab.example/merge_requests/1' ;;
  *) exit 1 ;;
esac
SH
chmod +x "$TMP/bin/gh" "$TMP/bin/glab"

new_repo() {
  local path="$1"
  git init -q -b main "$path"
  git -C "$path" config user.name "MEGAI Test"
  git -C "$path" config user.email "megai@example.test"
  printf 'base\n' >"$path/app.txt"
  git -C "$path" add app.txt
  git -C "$path" commit -qm "base"
  git -C "$path" branch dev
  git init -q --bare "$path.origin.git"
  git -C "$path" remote add origin "$path.origin.git"
  git -C "$path" push -q -u origin main dev
}

# A verified linked task worktree merges into dev, then only that linked
# worktree and its branch are removed. The primary repository survives.
repo="$TMP/linked-repo"
feature="$TMP/linked-feature"
new_repo "$repo"
git -C "$repo" worktree add -q -b agent/task "$feature" dev
printf 'feature\n' >>"$feature/app.txt"
git -C "$feature" add app.txt
git -C "$feature" commit -qm "feature"
if (cd "$feature" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --target dev) >/dev/null 2>&1; then
  echo "finish accepted work without --verified" >&2
  exit 1
fi
if (cd "$feature" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target main --pr-base dev) >/dev/null 2>&1; then
  echo "finish accepted protected target main" >&2
  exit 1
fi
if (cd "$feature" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev --pr-base master) >/dev/null 2>&1; then
  echo "finish accepted non-main PR base" >&2
  exit 1
fi
(cd "$feature" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null
[ -d "$repo/.git" ]
[ ! -e "$feature" ]
[ "$(git -C "$repo" show dev:app.txt)" = $'base\nfeature' ]
! git -C "$repo" show-ref --verify --quiet refs/heads/agent/task
[ "$(git -C "$repo" rev-parse dev)" = "$(git --git-dir="$repo.origin.git" rev-parse refs/heads/dev)" ]
grep -q '^pr list .*--base main .*--head dev' "$GH_LOG"
grep -q '^pr create .*--base main .*--head dev' "$GH_LOG"

# Independent implementation slices can start from the same dev baseline and
# integrate sequentially without losing either branch.
parallel_repo="$TMP/parallel-repo"
parallel_a="$TMP/parallel-a"
parallel_b="$TMP/parallel-b"
new_repo "$parallel_repo"
git -C "$parallel_repo" worktree add -q -b agent/parallel-a "$parallel_a" dev
git -C "$parallel_repo" worktree add -q -b agent/parallel-b "$parallel_b" dev
printf 'slice a\n' >"$parallel_a/a.txt"
git -C "$parallel_a" add a.txt
git -C "$parallel_a" commit -qm "slice a"
printf 'slice b\n' >"$parallel_b/b.txt"
git -C "$parallel_b" add b.txt
git -C "$parallel_b" commit -qm "slice b"
(cd "$parallel_a" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null
(cd "$parallel_b" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null
[ "$(git -C "$parallel_repo" show dev:a.txt)" = 'slice a' ]
[ "$(git -C "$parallel_repo" show dev:b.txt)" = 'slice b' ]
[ ! -e "$parallel_a" ]
[ ! -e "$parallel_b" ]
! git -C "$parallel_repo" show-ref --verify --quiet refs/heads/agent/parallel-a
! git -C "$parallel_repo" show-ref --verify --quiet refs/heads/agent/parallel-b
[ "$(git -C "$parallel_repo" rev-parse dev)" = "$(git --git-dir="$parallel_repo.origin.git" rev-parse refs/heads/dev)" ]

# Dirty worktrees fail closed and remain untouched.
dirty="$TMP/dirty-feature"
git -C "$repo" worktree add -q -b agent/dirty "$dirty" dev
printf 'dirty\n' >"$dirty/uncommitted.txt"
if (cd "$dirty" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null 2>&1; then
  echo "finish removed a dirty worktree" >&2
  exit 1
fi
[ -d "$dirty" ]
git -C "$repo" show-ref --verify --quiet refs/heads/agent/dirty
git -C "$repo" worktree remove --force "$dirty"
git -C "$repo" branch -D agent/dirty >/dev/null

# Failed post-merge verification restores dev and preserves source work.
verify_repo="$TMP/verify-repo"
verify_feature="$TMP/verify-feature"
new_repo "$verify_repo"
git -C "$verify_repo" worktree add -q -b agent/verify "$verify_feature" dev
printf 'verify feature\n' >>"$verify_feature/app.txt"
git -C "$verify_feature" add app.txt
git -C "$verify_feature" commit -qm "verify feature"
dev_before="$(git -C "$verify_repo" rev-parse dev)"
if (cd "$verify_feature" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev --verify-command 'touch verification-artifact && false') >/dev/null 2>&1; then
  echo "finish accepted failed post-merge verification" >&2
  exit 1
fi
[ "$(git -C "$verify_repo" rev-parse dev)" = "$dev_before" ]
[ -d "$verify_feature" ]
git -C "$verify_repo" show-ref --verify --quiet refs/heads/agent/verify
git -C "$verify_repo" worktree remove --force "$verify_feature"
git -C "$verify_repo" branch -D agent/verify >/dev/null

# PR creation failure preserves the source worktree/branch for recovery even
# though the verified dev merge was already pushed.
pr_fail_repo="$TMP/pr-fail-repo"
pr_fail_feature="$TMP/pr-fail-feature"
new_repo "$pr_fail_repo"
git -C "$pr_fail_repo" worktree add -q -b agent/pr-fail "$pr_fail_feature" dev
printf 'pr failure work\n' >>"$pr_fail_feature/app.txt"
git -C "$pr_fail_feature" add app.txt
git -C "$pr_fail_feature" commit -qm "pr failure work"
if (cd "$pr_fail_feature" && GH_FAIL_CREATE=1 MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null 2>&1; then
  echo "finish accepted failed PR creation" >&2
  exit 1
fi
[ -d "$pr_fail_feature" ]
git -C "$pr_fail_repo" show-ref --verify --quiet refs/heads/agent/pr-fail
[ "$(git -C "$pr_fail_repo" rev-parse dev)" = "$(git --git-dir="$pr_fail_repo.origin.git" rev-parse refs/heads/dev)" ]
git -C "$pr_fail_repo" worktree remove --force "$pr_fail_feature"
git -C "$pr_fail_repo" branch -D agent/pr-fail >/dev/null

# Merge conflicts abort without deleting the source worktree or branch.
conflict_repo="$TMP/conflict-repo"
conflict_feature="$TMP/conflict-feature"
new_repo "$conflict_repo"
git -C "$conflict_repo" worktree add -q -b agent/conflict "$conflict_feature" main
printf 'dev change\n' >"$conflict_repo/app.txt"
git -C "$conflict_repo" add app.txt
git -C "$conflict_repo" commit -qm "main setup"
git -C "$conflict_repo" switch -q dev
git -C "$conflict_repo" cherry-pick main >/dev/null
printf 'dev version\n' >"$conflict_repo/app.txt"
git -C "$conflict_repo" commit -qam "dev version"
printf 'feature version\n' >"$conflict_feature/app.txt"
git -C "$conflict_feature" commit -qam "feature version"
dev_before="$(git -C "$conflict_repo" rev-parse dev)"
if (cd "$conflict_feature" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null 2>&1; then
  echo "finish accepted a merge conflict" >&2
  exit 1
fi
[ "$(git -C "$conflict_repo" rev-parse dev)" = "$dev_before" ]
[ -d "$conflict_feature" ]
git -C "$conflict_repo" show-ref --verify --quiet refs/heads/agent/conflict
git -C "$conflict_repo" worktree remove --force "$conflict_feature"
git -C "$conflict_repo" branch -D agent/conflict >/dev/null

# A feature branch in the primary checkout is merged without deleting the
# repository; the checkout lands on dev and the feature branch is deleted.
primary="$TMP/primary-repo"
new_repo "$primary"
git -C "$primary" switch -qc agent/primary main
printf 'primary feature\n' >>"$primary/app.txt"
git -C "$primary" add app.txt
git -C "$primary" commit -qm "primary feature"
(cd "$primary" && MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null
[ -d "$primary/.git" ]
[ "$(git -C "$primary" branch --show-current)" = dev ]
[ "$(git -C "$primary" show dev:app.txt)" = $'base\nprimary feature' ]
! git -C "$primary" show-ref --verify --quiet refs/heads/agent/primary

# Work committed directly on dev is published without deleting or switching the
# primary repository, and an existing PR is reused instead of duplicated.
direct="$TMP/direct-repo"
new_repo "$direct"
git -C "$direct" switch -q dev
printf 'direct dev work\n' >>"$direct/app.txt"
git -C "$direct" add app.txt
git -C "$direct" commit -qm "direct dev work"
: >"$GH_LOG"
(cd "$direct" && GH_EXISTING_URL='https://github.example/pull/existing' MEGAI_FORGE=github MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null
[ -d "$direct/.git" ]
[ "$(git -C "$direct" branch --show-current)" = dev ]
grep -q '^pr list .*--base main .*--head dev' "$GH_LOG"
! grep -q '^pr create ' "$GH_LOG"

# GitLab uses a merge request with dev as source and main as target.
gitlab_repo="$TMP/gitlab-repo"
gitlab_feature="$TMP/gitlab-feature"
new_repo "$gitlab_repo"
git -C "$gitlab_repo" worktree add -q -b agent/gitlab "$gitlab_feature" dev
printf 'gitlab work\n' >>"$gitlab_feature/app.txt"
git -C "$gitlab_feature" add app.txt
git -C "$gitlab_feature" commit -qm "gitlab work"
: >"$GLAB_LOG"
(cd "$gitlab_feature" && MEGAI_FORGE=gitlab MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" finish --verified --target dev) >/dev/null
[ ! -e "$gitlab_feature" ]
grep -q '^mr list .*--source-branch dev .*--target-branch main' "$GLAB_LOG"
grep -q '^mr create .*--source-branch dev .*--target-branch main' "$GLAB_LOG"

# Primary checkouts default from main to dev, but dirty work is never switched.
dev_repo="$TMP/dev-repo"
new_repo "$dev_repo"
(cd "$dev_repo" && MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" dev) >/dev/null
[ "$(git -C "$dev_repo" branch --show-current)" = dev ]
master_repo="$TMP/master-repo"
git init -q -b master "$master_repo"
git -C "$master_repo" config user.name "MEGAI Test"
git -C "$master_repo" config user.email "megai@example.test"
printf 'base\n' >"$master_repo/app.txt"
git -C "$master_repo" add app.txt
git -C "$master_repo" commit -qm "base"
(cd "$master_repo" && MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" dev) >/dev/null
[ "$(git -C "$master_repo" branch --show-current)" = dev ]
[ "$(git -C "$master_repo" config branch.dev.gh-merge-base)" = master ]
linked_primary="$TMP/linked-dev-primary"
linked_dev="$TMP/linked-dev-worktree"
new_repo "$linked_primary"
git -C "$linked_primary" worktree add -q "$linked_dev" dev
if (cd "$linked_dev" && MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" dev) >/dev/null 2>&1; then
  echo "megai dev accepted a linked dev worktree" >&2
  exit 1
fi
git -C "$linked_primary" worktree remove "$linked_dev"
dirty_dev_repo="$TMP/dirty-dev-repo"
new_repo "$dirty_dev_repo"
printf 'dirty\n' >"$dirty_dev_repo/uncommitted.txt"
if (cd "$dirty_dev_repo" && MEGAI_HOME="$ROOT" bash "$ROOT/bin/megai" dev) >/dev/null 2>&1; then
  echo "megai dev switched a dirty main checkout" >&2
  exit 1
fi
[ "$(git -C "$dirty_dev_repo" branch --show-current)" = main ]

# Global installation reaches all four harnesses and preserves user policy.
export HOME="$TMP/home"
export MEGAI_HOME="$TMP/megai"
mkdir -p "$MEGAI_HOME/skills/agent-worktree-lifecycle" "$MEGAI_HOME/skills/smart-development-orchestrator" "$MEGAI_HOME/lib"
cp "$ROOT/skills/agent-worktree-lifecycle/SKILL.md" "$MEGAI_HOME/skills/agent-worktree-lifecycle/SKILL.md"
cp "$ROOT/skills/smart-development-orchestrator/SKILL.md" "$MEGAI_HOME/skills/smart-development-orchestrator/SKILL.md"
cp "$ROOT/lib/ui.sh" "$ROOT/lib/state.sh" "$ROOT/lib/install_worktree_lifecycle.sh" "$MEGAI_HOME/lib/"
mkdir -p "$HOME/.codex" "$HOME/.pi/agent" "$HOME/.claude" "$HOME/.omp/agent"
printf 'codex user policy\n' >"$HOME/.codex/AGENTS.md"
printf 'pi user policy\n' >"$HOME/.pi/agent/AGENTS.md"
printf 'claude user policy\n' >"$HOME/.claude/CLAUDE.md"
printf 'omp user policy\n' >"$HOME/.omp/agent/RULES.md"
printf '{"tools":{},"agents":{},"projects":{}}\n' >"$MEGAI_HOME/state.json"
collision_skill="$HOME/.omp/profiles/collision/agent/skills/agent-worktree-lifecycle/SKILL.md"
mkdir -p "$(dirname "$collision_skill")"
printf '%s\n' 'user-owned lifecycle skill' >"$collision_skill"
bash "$MEGAI_HOME/lib/install_worktree_lifecycle.sh" >/dev/null
bash "$MEGAI_HOME/lib/install_worktree_lifecycle.sh" >/dev/null
grep -q '^user-owned lifecycle skill$' "$collision_skill"
for skill in \
  "$HOME/.agents/skills/agent-worktree-lifecycle/SKILL.md" \
  "$HOME/.claude/skills/agent-worktree-lifecycle/SKILL.md" \
  "$HOME/.pi/agent/skills/agent-worktree-lifecycle/SKILL.md" \
  "$HOME/.omp/agent/skills/agent-worktree-lifecycle/SKILL.md" \
  "$HOME/.agents/skills/smart-development-orchestrator/SKILL.md" \
  "$HOME/.claude/skills/smart-development-orchestrator/SKILL.md" \
  "$HOME/.pi/agent/skills/smart-development-orchestrator/SKILL.md" \
  "$HOME/.omp/agent/skills/smart-development-orchestrator/SKILL.md"; do
  [ -f "$skill" ]
  grep -q '^managed-by: megai$' "$skill"
done
grep -q 'Free OpenCode dispatch is also default-deny' "$HOME/.claude/skills/smart-development-orchestrator/SKILL.md"
grep -q 'operator-approved provider privacy attestation' "$HOME/.claude/skills/smart-development-orchestrator/SKILL.md"
for policy in "$HOME/.codex/AGENTS.md" "$HOME/.pi/agent/AGENTS.md" "$HOME/.claude/CLAUDE.md" "$HOME/.omp/agent/RULES.md"; do
  grep -q 'user policy' "$policy"
  [ "$(grep -c 'megai:worktree-lifecycle:begin' "$policy")" = 1 ]
  grep -q 'megai dev' "$policy"
  grep -q 'megai finish --verified --target dev' "$policy"
  grep -q 'dev.*main.*PR/MR' "$policy"
  grep -q 'fan them out concurrently in one batch' "$policy"
  grep -q 'one registered Paseo/OMP/Git worktree' "$policy"
  grep -q 'Never auto-merge `main`' "$policy"
  grep -q 'smart-development-orchestrator' "$policy"
  grep -q 'same-workspace subagent tabs' "$policy"
  grep -q 'archive_workspace' "$policy"
  grep -q 'Never archive the primary `dev` workspace' "$policy"
done
bash "$MEGAI_HOME/lib/install_worktree_lifecycle.sh" --remove >/dev/null
grep -q '^user-owned lifecycle skill$' "$collision_skill"
for skill in \
  "$HOME/.agents/skills/agent-worktree-lifecycle" \
  "$HOME/.claude/skills/agent-worktree-lifecycle" \
  "$HOME/.pi/agent/skills/agent-worktree-lifecycle" \
  "$HOME/.omp/agent/skills/agent-worktree-lifecycle" \
  "$HOME/.agents/skills/smart-development-orchestrator" \
  "$HOME/.claude/skills/smart-development-orchestrator" \
  "$HOME/.pi/agent/skills/smart-development-orchestrator" \
  "$HOME/.omp/agent/skills/smart-development-orchestrator"; do
  [ ! -e "$skill" ]
done
for policy in "$HOME/.codex/AGENTS.md" "$HOME/.pi/agent/AGENTS.md" "$HOME/.claude/CLAUDE.md" "$HOME/.omp/agent/RULES.md"; do
  grep -q 'user policy' "$policy"
  ! grep -q 'megai:worktree-lifecycle:begin' "$policy"
done

echo "Worktree lifecycle: ok"
