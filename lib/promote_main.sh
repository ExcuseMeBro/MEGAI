#!/usr/bin/env bash
# Merge the reviewed dev-to-main change request only after explicit approval.
set -euo pipefail

SOURCE=dev
TARGET=main
FORGE="${MEGAI_FORGE:-auto}"
APPROVED=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: megai promote --approved [--source dev] [--target main] [--forge auto|github|gitlab] [--dry-run]

Merges the one open dev-to-main pull/merge request after explicit user approval,
keeps dev available for future task work, and synchronizes the local main branch.
EOF
}

die() {
  printf 'megai promote: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --approved) APPROVED=1 ;;
    --source)
      [ "$#" -ge 2 ] || die "--source requires a branch"
      SOURCE="$2"
      shift
      ;;
    --target)
      [ "$#" -ge 2 ] || die "--target requires a branch"
      TARGET="$2"
      shift
      ;;
    --forge)
      [ "$#" -ge 2 ] || die "--forge requires auto, github, or gitlab"
      FORGE="$2"
      shift
      ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done

[ "$SOURCE" = dev ] || die "--source is fixed to dev"
[ "$TARGET" = main ] || die "--target is fixed to main"
[ "$DRY_RUN" = 1 ] || [ "$APPROVED" = 1 ] || die "explicit user approval required: pass --approved"
case "$FORGE" in auto|github|gitlab) ;; *) die "--forge must be auto, github, or gitlab" ;; esac

command -v git >/dev/null 2>&1 || die "git is required"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run inside a Git worktree"
[ -z "$(git status --porcelain --untracked-files=all)" ] || die "current worktree is dirty"

PRIMARY_ROOT="$(git worktree list --porcelain | awk '/^worktree / { print substr($0, 10); exit }')"
[ -n "$PRIMARY_ROOT" ] || die "could not resolve the primary repository"
PRIMARY_ROOT="$(cd "$PRIMARY_ROOT" && pwd -P)"
COMMON_DIR="$(git rev-parse --git-common-dir)"
COMMON_DIR="$(cd "$COMMON_DIR" && pwd -P)"
REMOTE_URL="$(git remote get-url origin 2>/dev/null)" || die "origin remote is required"

if [ "$FORGE" = auto ]; then
  case "$REMOTE_URL" in
    *github.com*|*github.*) FORGE=github ;;
    *gitlab.com*|*gitlab.*|*gitlab*) FORGE=gitlab ;;
    *) die "cannot detect forge from origin; pass --forge github or --forge gitlab" ;;
  esac
fi
if [ "$FORGE" = github ]; then
  command -v gh >/dev/null 2>&1 || die "GitHub CLI is required"
else
  command -v glab >/dev/null 2>&1 || die "GitLab CLI is required"
  command -v jq >/dev/null 2>&1 || die "jq is required for GitLab merge-request lookup"
fi

git -C "$PRIMARY_ROOT" fetch -q origin "$SOURCE" "$TARGET" || die "failed to fetch origin/$SOURCE and origin/$TARGET"
for branch in "$SOURCE" "$TARGET"; do
  git -C "$PRIMARY_ROOT" show-ref --verify --quiet "refs/remotes/origin/$branch" || die "origin/$branch is missing"
done
if ! git -C "$PRIMARY_ROOT" show-ref --verify --quiet "refs/heads/$SOURCE"; then
  git -C "$PRIMARY_ROOT" branch --track "$SOURCE" "origin/$SOURCE" >/dev/null
fi
DEV_HEAD="$(git -C "$PRIMARY_ROOT" rev-parse "refs/heads/$SOURCE")"
[ "$DEV_HEAD" = "$(git -C "$PRIMARY_ROOT" rev-parse "refs/remotes/origin/$SOURCE")" ] ||
  die "local $SOURCE is not fully pushed to origin/$SOURCE"

if git -C "$PRIMARY_ROOT" merge-base --is-ancestor "$DEV_HEAD" "refs/remotes/origin/$TARGET"; then
  printf "origin/%s already contains the published %s head %s.\n" "$TARGET" "$SOURCE" "$DEV_HEAD"
  exit 0
fi

CHANGE_URL=""
if [ "$FORGE" = github ]; then
  record="$(cd "$PRIMARY_ROOT" && gh pr list --base "$TARGET" --head "$SOURCE" --state open --json url,headRefOid,mergeable,mergeStateStatus --jq 'if length == 0 then empty else [.[0].url, .[0].headRefOid, .[0].mergeable, .[0].mergeStateStatus] | @tsv end')" ||
    die "GitHub PR lookup failed"
  [ -n "$record" ] || die "no open $SOURCE-to-$TARGET pull request exists"
  IFS=$'\t' read -r CHANGE_URL CHANGE_HEAD MERGEABLE MERGE_STATE <<EOF
$record
EOF
  [ "$CHANGE_HEAD" = "$DEV_HEAD" ] || die "pull-request head changed; review the latest dev commit before promotion"
  [ "$MERGEABLE" = MERGEABLE ] || die "pull request is not mergeable"
  [ "$MERGE_STATE" = CLEAN ] || die "pull request checks or protections are not clean: $MERGE_STATE"
else
  json="$(cd "$PRIMARY_ROOT" && glab mr list --source-branch "$SOURCE" --target-branch "$TARGET" --state opened --output json)" ||
    die "GitLab merge-request lookup failed"
  CHANGE_URL="$(printf '%s' "$json" | jq -r '.[0].web_url // empty')"
  [ -n "$CHANGE_URL" ] || die "no open $SOURCE-to-$TARGET merge request exists"
fi

if [ "$DRY_RUN" = 1 ]; then
  printf "Would merge the reviewed %s-to-%s request after explicit approval: %s\n" "$SOURCE" "$TARGET" "$CHANGE_URL"
  printf "Would keep %s, push/synchronize %s, and create no additional request.\n" "$SOURCE" "$TARGET"
  exit 0
fi

LOCK_DIR="$COMMON_DIR/megai-promote.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  die "another main promotion is active for this repository"
fi
TEMP_PARENT=""
MAIN_WORKTREE=""
cleanup() {
  if [ -n "$TEMP_PARENT" ] && [ -n "$MAIN_WORKTREE" ]; then
    git -C "$PRIMARY_ROOT" worktree remove --force "$MAIN_WORKTREE" >/dev/null 2>&1 || true
  fi
  [ -z "$TEMP_PARENT" ] || rm -rf "$TEMP_PARENT" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if ! git -C "$PRIMARY_ROOT" show-ref --verify --quiet "refs/heads/$TARGET"; then
  git -C "$PRIMARY_ROOT" branch --track "$TARGET" "origin/$TARGET" >/dev/null
fi
MAIN_WORKTREE="$(git -C "$PRIMARY_ROOT" worktree list --porcelain | awk -v ref="refs/heads/$TARGET" '
  /^worktree / { path=substr($0, 10) }
  $0 == "branch " ref { print path; exit }
')"
if [ -z "$MAIN_WORKTREE" ]; then
  TEMP_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/megai-promote.XXXXXX")"
  MAIN_WORKTREE="$TEMP_PARENT/main"
  git -C "$PRIMARY_ROOT" worktree add -q "$MAIN_WORKTREE" "$TARGET"
fi
[ -z "$(git -C "$MAIN_WORKTREE" status --porcelain --untracked-files=all)" ] || die "main worktree '$MAIN_WORKTREE' is dirty"
[ "$(git -C "$MAIN_WORKTREE" rev-parse HEAD)" = "$(git -C "$PRIMARY_ROOT" rev-parse refs/remotes/origin/$TARGET)" ] ||
  die "local $TARGET differs from origin/$TARGET; synchronize it before promotion"

if [ "$FORGE" = github ]; then
  (cd "$PRIMARY_ROOT" && gh pr merge "$CHANGE_URL" --merge --match-head-commit "$DEV_HEAD") || die "GitHub PR merge failed"
else
  (cd "$PRIMARY_ROOT" && glab mr merge "$SOURCE" --sha "$DEV_HEAD" --auto-merge=false --yes) || die "GitLab merge-request merge failed"
fi

git -C "$PRIMARY_ROOT" fetch -q origin "$TARGET" || die "request merged, but origin/$TARGET refresh failed"
if ! git -C "$PRIMARY_ROOT" ls-remote --exit-code --heads origin "$SOURCE" >/dev/null 2>&1; then
  git -C "$PRIMARY_ROOT" push -u origin "$SOURCE" || die "request merged, but persistent origin/$SOURCE could not be restored"
fi
git -C "$MAIN_WORKTREE" merge --ff-only "origin/$TARGET" >/dev/null ||
  die "request merged, but local $TARGET could not fast-forward to origin/$TARGET"
git -C "$MAIN_WORKTREE" merge-base --is-ancestor "$DEV_HEAD" HEAD ||
  die "origin/$TARGET does not contain the approved $SOURCE head after merge"

printf "Merged the approved request into '%s', synchronized local/origin %s, and preserved '%s'.\n" \
  "$TARGET" "$TARGET" "$SOURCE"
