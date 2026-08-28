#!/usr/bin/env bash
# Merge a verified task branch into local dev and remove only its registered
# agent worktree/branch. Fails closed on ambiguity, dirty state, or conflicts.
set -euo pipefail

TARGET=dev
PR_BASE=main
FORGE="${MEGAI_FORGE:-auto}"
VERIFIED=0
DRY_RUN=0
VERIFY_COMMAND=""

usage() {
  cat <<'EOF'
Usage: megai finish --verified [--target dev] [--pr-base main] [--forge auto|github|gitlab] [--verify-command "command"] [--dry-run]

Merges a task branch into dev (or publishes work already on dev), pushes dev,
and creates or reuses a dev-to-main pull/merge request. It then removes only
the merged task branch and registered linked worktree. The primary repository
and remote branches are never deleted; the PR/MR is never auto-merged.
EOF
}

die() {
  printf 'megai finish: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --verified) VERIFIED=1 ;;
    --target)
      [ "$#" -ge 2 ] || die "--target requires a branch"
      TARGET="$2"
      shift
      ;;
    --pr-base)
      [ "$#" -ge 2 ] || die "--pr-base requires a branch"
      PR_BASE="$2"
      shift
      ;;
    --forge)
      [ "$#" -ge 2 ] || die "--forge requires auto, github, or gitlab"
      FORGE="$2"
      shift
      ;;
    --verify-command)
      [ "$#" -ge 2 ] || die "--verify-command requires a command"
      VERIFY_COMMAND="$2"
      shift
      ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown option: $1" ;;
  esac
  shift
done
[ "$TARGET" = dev ] || die "--target is fixed to dev"
[ "$PR_BASE" = main ] || die "--pr-base is fixed to main"

command -v git >/dev/null 2>&1 || die "git is required"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "run inside a Git worktree"

SOURCE_ROOT="$(git rev-parse --show-toplevel)"
SOURCE_ROOT="$(cd "$SOURCE_ROOT" && pwd -P)"
SOURCE_BRANCH="$(git branch --show-current)"
[ -n "$SOURCE_BRANCH" ] || die "detached HEAD is not a task branch"
SOURCE_HEAD="$(git rev-parse HEAD)"
DIRECT_TARGET=0
if [ "$SOURCE_BRANCH" = "$TARGET" ]; then
  DIRECT_TARGET=1
else
  case "$SOURCE_BRANCH" in
    main|master|develop|production|prod)
      die "refusing to ship protected branch '$SOURCE_BRANCH'; switch to dev or a task branch"
      ;;
  esac
fi

[ "$DRY_RUN" = 1 ] || [ "$VERIFIED" = 1 ] || die "verification attestation required: pass --verified"
[ -z "$(git status --porcelain --untracked-files=all)" ] || die "current worktree is dirty"

git check-ref-format --branch "$TARGET" >/dev/null 2>&1 || die "invalid target branch '$TARGET'"
git check-ref-format --branch "$PR_BASE" >/dev/null 2>&1 || die "invalid PR base branch '$PR_BASE'"
[ "$TARGET" != "$PR_BASE" ] || die "target and PR base branches must differ"
case "$FORGE" in auto|github|gitlab) ;; *) die "--forge must be auto, github, or gitlab" ;; esac
REMOTE_URL="$(git remote get-url origin 2>/dev/null)" || die "origin remote is required for dev-to-main PRs"
if [ "$FORGE" = auto ]; then
  case "$REMOTE_URL" in
    *github.com*|*github.*) FORGE=github ;;
    *gitlab.com*|*gitlab.*|*gitlab*) FORGE=gitlab ;;
    *) die "cannot detect forge from origin; pass --forge github or --forge gitlab" ;;
  esac
fi
command -v "$([ "$FORGE" = github ] && printf gh || printf glab)" >/dev/null 2>&1 || die "$FORGE CLI is required"
if ! git show-ref --verify --quiet "refs/heads/$PR_BASE" && ! git show-ref --verify --quiet "refs/remotes/origin/$PR_BASE"; then
  die "PR base '$PR_BASE' is missing locally and at origin"
fi
COMMON_DIR="$(git rev-parse --git-common-dir)"
COMMON_DIR="$(cd "$COMMON_DIR" && pwd -P)"
PRIMARY_ROOT="$(git worktree list --porcelain | awk '/^worktree / { print substr($0, 10); exit }')"
[ -n "$PRIMARY_ROOT" ] || die "could not resolve the primary repository"
PRIMARY_ROOT="$(cd "$PRIMARY_ROOT" && pwd -P)"

TARGET_EXISTS=1
if ! git show-ref --verify --quiet "refs/heads/$TARGET"; then
  TARGET_EXISTS=0
  if ! git show-ref --verify --quiet "refs/remotes/origin/$TARGET"; then
    die "local '$TARGET' and 'origin/$TARGET' are missing; create the integration branch explicitly"
  fi
fi

TARGET_WORKTREE="$(git worktree list --porcelain | awk -v ref="refs/heads/$TARGET" '
  /^worktree / { path=substr($0, 10) }
  $0 == "branch " ref { print path; exit }
')"
if [ -n "$TARGET_WORKTREE" ]; then
  TARGET_WORKTREE="$(cd "$TARGET_WORKTREE" && pwd -P)"
fi

if [ "$DIRECT_TARGET" = 0 ] && [ "$SOURCE_ROOT" = "$PRIMARY_ROOT" ] && [ -n "$TARGET_WORKTREE" ] && [ "$TARGET_WORKTREE" != "$SOURCE_ROOT" ]; then
  die "primary checkout cannot be cleaned while '$TARGET' is checked out in another worktree"
fi

if [ "$DRY_RUN" = 1 ]; then
  if [ "$DIRECT_TARGET" = 1 ]; then
    printf 'Would publish verified work already on %s.\n' "$TARGET"
  else
    printf 'Would merge %s into %s locally.\n' "$SOURCE_BRANCH" "$TARGET"
    if [ "$SOURCE_ROOT" = "$PRIMARY_ROOT" ]; then
      printf 'Would keep primary repository %s, switch it to %s, and delete branch %s.\n' "$SOURCE_ROOT" "$TARGET" "$SOURCE_BRANCH"
    else
      printf 'Would remove linked worktree %s and delete branch %s after merge.\n' "$SOURCE_ROOT" "$SOURCE_BRANCH"
    fi
  fi
  [ "$TARGET_EXISTS" = 1 ] || printf 'Would create local %s tracking origin/%s.\n' "$TARGET" "$TARGET"
  printf 'Would push %s to origin and create or reuse a %s-to-%s %s request via %s.\n' "$TARGET" "$TARGET" "$PR_BASE" "$([ "$FORGE" = github ] && printf pull || printf merge)" "$FORGE"
  exit 0
fi

LOCK_DIR="$COMMON_DIR/megai-finish.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  die "another merge/cleanup is active for this repository"
fi

TEMP_PARENT=""
TEMP_TARGET=0
VERIFY_PARENT=""
VERIFY_WORKTREE=""
cleanup() {
  if [ -n "$VERIFY_WORKTREE" ]; then
    git -C "$PRIMARY_ROOT" worktree remove --force "$VERIFY_WORKTREE" >/dev/null 2>&1 || true
  fi
  [ -z "$VERIFY_PARENT" ] || rm -rf "$VERIFY_PARENT" 2>/dev/null || true
  if [ "$TEMP_TARGET" = 1 ] && [ -n "$TARGET_WORKTREE" ]; then
    git -C "$PRIMARY_ROOT" worktree remove --force "$TARGET_WORKTREE" >/dev/null 2>&1 || true
  fi
  [ -z "$TEMP_PARENT" ] || rm -rf "$TEMP_PARENT" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

open_change_request() {
  local existing title body
  title="Promote $TARGET to $PR_BASE"
  body="Automated by MEGAI after verified task work was integrated into $TARGET. Review and merge manually."
  PR_URL=""
  if [ "$FORGE" = github ]; then
    if ! existing="$(cd "$TARGET_WORKTREE" && gh pr list --base "$PR_BASE" --head "$TARGET" --state open --json url --jq '.[0].url // empty')"; then
      die "GitHub PR lookup failed; '$SOURCE_BRANCH' was preserved"
    fi
    if [ -n "$existing" ]; then
      PR_URL="$existing"
    elif ! PR_URL="$(cd "$TARGET_WORKTREE" && gh pr create --base "$PR_BASE" --head "$TARGET" --title "$title" --body "$body")"; then
      die "GitHub PR creation failed; '$SOURCE_BRANCH' was preserved"
    fi
  else
    if ! existing="$(cd "$TARGET_WORKTREE" && glab mr list --source-branch "$TARGET" --target-branch "$PR_BASE" --output json --jq '.[0].web_url // empty')"; then
      die "GitLab merge-request lookup failed; '$SOURCE_BRANCH' was preserved"
    fi
    if [ -n "$existing" ]; then
      PR_URL="$existing"
    elif ! PR_URL="$(cd "$TARGET_WORKTREE" && glab mr create --source-branch "$TARGET" --target-branch "$PR_BASE" --title "$title" --description "$body" --remove-source-branch=false --yes)"; then
      die "GitLab merge-request creation failed; '$SOURCE_BRANCH' was preserved"
    fi
  fi
}

if [ "$TARGET_EXISTS" = 0 ]; then
  git branch --track "$TARGET" "origin/$TARGET" >/dev/null
fi

if [ -z "$TARGET_WORKTREE" ]; then
  TEMP_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/megai-finish.XXXXXX")"
  TARGET_WORKTREE="$TEMP_PARENT/target"
  git -C "$PRIMARY_ROOT" worktree add -q "$TARGET_WORKTREE" "$TARGET"
  TEMP_TARGET=1
fi

[ -z "$(git -C "$TARGET_WORKTREE" status --porcelain --untracked-files=all)" ] || die "target worktree '$TARGET_WORKTREE' is dirty"
TARGET_BEFORE="$(git -C "$TARGET_WORKTREE" rev-parse HEAD)"

if [ "$DIRECT_TARGET" = 0 ]; then
  [ "$(git rev-parse "$SOURCE_BRANCH")" = "$SOURCE_HEAD" ] ||
    die "source branch advanced before merge; no target changes were made"
  if ! git -C "$TARGET_WORKTREE" merge --no-ff --no-edit "$SOURCE_HEAD"; then
    git -C "$TARGET_WORKTREE" merge --abort >/dev/null 2>&1 || true
    die "merge conflict; source worktree and branch were preserved"
  fi
fi

MERGED_HEAD="$(git -C "$TARGET_WORKTREE" rev-parse HEAD)"
if [ -n "$VERIFY_COMMAND" ]; then
  VERIFY_PARENT="$(mktemp -d "${TMPDIR:-/tmp}/megai-verify.XXXXXX")"
  VERIFY_WORKTREE="$VERIFY_PARENT/worktree"
  git -C "$PRIMARY_ROOT" worktree add -q --detach "$VERIFY_WORKTREE" "$MERGED_HEAD"
  verify_ok=1
  (cd "$VERIFY_WORKTREE" && /bin/sh -lc "$VERIFY_COMMAND") || verify_ok=0
  git -C "$PRIMARY_ROOT" worktree remove --force "$VERIFY_WORKTREE"
  VERIFY_WORKTREE=""
  rm -rf "$VERIFY_PARENT"
  VERIFY_PARENT=""
  if [ "$verify_ok" = 0 ]; then
    if [ "$(git -C "$TARGET_WORKTREE" rev-parse HEAD)" != "$MERGED_HEAD" ] ||
      [ -n "$(git -C "$TARGET_WORKTREE" status --porcelain --untracked-files=all)" ]; then
      die "post-merge verification failed and '$TARGET' changed concurrently; source work was preserved for manual recovery"
    fi
    git -C "$TARGET_WORKTREE" reset --hard "$TARGET_BEFORE" >/dev/null
    die "post-merge verification failed; '$TARGET' was restored and source work was preserved"
  fi
fi

if [ "$(git rev-parse "$SOURCE_BRANCH")" != "$SOURCE_HEAD" ] || [ -n "$(git -C "$SOURCE_ROOT" status --porcelain --untracked-files=all)" ]; then
  die "source changed during merge/verification; '$TARGET' contains the merge but source worktree and branch were preserved"
fi
if [ "$(git -C "$TARGET_WORKTREE" rev-parse HEAD)" != "$MERGED_HEAD" ] ||
  [ -n "$(git -C "$TARGET_WORKTREE" status --porcelain --untracked-files=all)" ]; then
  die "target changed during merge/verification; source worktree and branch were preserved"
fi

if ! git -C "$TARGET_WORKTREE" push -u origin "$TARGET"; then
  die "push of '$TARGET' failed; local merge and source work were preserved"
fi
open_change_request
if [ "$(git rev-parse "$SOURCE_BRANCH")" != "$SOURCE_HEAD" ] ||
  [ -n "$(git -C "$SOURCE_ROOT" status --porcelain --untracked-files=all)" ] ||
  [ "$(git -C "$TARGET_WORKTREE" rev-parse HEAD)" != "$MERGED_HEAD" ] ||
  [ -n "$(git -C "$TARGET_WORKTREE" status --porcelain --untracked-files=all)" ]; then
  die "repository changed during push/PR creation; PR remains open and source cleanup was skipped"
fi

if [ "$DIRECT_TARGET" = 1 ]; then
  printf "Published verified '%s' and opened/reused the %s request to '%s': %s\n" \
    "$TARGET" "$([ "$FORGE" = github ] && printf pull || printf merge)" "$PR_BASE" "$PR_URL"
  exit 0
fi

if [ "$SOURCE_ROOT" = "$PRIMARY_ROOT" ]; then
  [ "$TEMP_TARGET" = 1 ] || die "internal safety check failed for primary checkout"
  git -C "$PRIMARY_ROOT" worktree remove "$TARGET_WORKTREE"
  TEMP_TARGET=0
  rm -rf "$TEMP_PARENT"
  TEMP_PARENT=""
  TARGET_WORKTREE=""
  git -C "$SOURCE_ROOT" switch -q "$TARGET"
  git -C "$SOURCE_ROOT" branch -d "$SOURCE_BRANCH" >/dev/null
  printf "Merged '%s' into '%s'; primary repository kept at %s and switched to %s.\n" \
    "$SOURCE_BRANCH" "$TARGET" "$SOURCE_ROOT" "$TARGET"
else
  git -C "$TARGET_WORKTREE" worktree remove "$SOURCE_ROOT"
  git -C "$TARGET_WORKTREE" branch -d "$SOURCE_BRANCH" >/dev/null
  if [ "$TEMP_TARGET" = 1 ]; then
    git -C "$PRIMARY_ROOT" worktree remove "$TARGET_WORKTREE"
    TEMP_TARGET=0
    rm -rf "$TEMP_PARENT"
    TEMP_PARENT=""
    TARGET_WORKTREE=""
  fi
  printf "Merged '%s' into '%s'; removed linked worktree %s and deleted the merged branch.\n" \
    "$SOURCE_BRANCH" "$TARGET" "$SOURCE_ROOT"
fi

printf "Opened/reused the %s request from '%s' to '%s': %s\n" \
  "$([ "$FORGE" = github ] && printf pull || printf merge)" "$TARGET" "$PR_BASE" "$PR_URL"
printf 'The request remains open for human review; main was not merged automatically.\n'
