#!/usr/bin/env bash
# Keep primary development on local dev without disrupting active task branches.
set -euo pipefail

MODE="${1:-strict}"
case "$MODE" in strict|--launch) ;; *) printf 'Usage: megai dev\n' >&2; exit 1 ;; esac

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  [ "$MODE" = "--launch" ] && exit 0
  printf 'megai dev: run inside a Git worktree\n' >&2
  exit 1
fi

root="$(git rev-parse --show-toplevel)"
root="$(cd "$root" && pwd -P)"
branch="$(git branch --show-current)"
[ -n "$branch" ] || { printf 'megai dev: detached HEAD is unsupported\n' >&2; exit 1; }

primary_root="$(git worktree list --porcelain | awk '/^worktree / { print substr($0, 10); exit }')"
[ -n "$primary_root" ] || { printf 'megai dev: cannot resolve the primary worktree\n' >&2; exit 1; }
primary_root="$(cd "$primary_root" && pwd -P)"
if [ "$root" != "$primary_root" ]; then
  if [ "$MODE" = "--launch" ]; then
    printf "Linked task worktree kept: %s (integration target: dev).\n" "$branch"
    exit 0
  fi
  printf "megai dev: refusing to switch linked worktree '%s'; run from primary checkout %s\n" "$root" "$primary_root" >&2
  exit 1
fi

base_branch=""
case "$branch" in
  main|master) base_branch="$branch" ;;
esac
if [ -z "$base_branch" ]; then
  if git show-ref --verify --quiet refs/heads/main || git show-ref --verify --quiet refs/remotes/origin/main; then
    base_branch=main
  elif git show-ref --verify --quiet refs/heads/master || git show-ref --verify --quiet refs/remotes/origin/master; then
    base_branch=master
  fi
fi
[ -n "$base_branch" ] || {
  printf "megai dev: cannot resolve main/master locally or at origin\n" >&2
  exit 1
}

if [ "$branch" = dev ]; then
  git config branch.dev.gh-merge-base "$base_branch"
  printf "Development branch ready: %s (dev).\n" "$root"
  exit 0
fi

case "$branch" in
  main|master) ;;
  *)
    if [ "$MODE" = "--launch" ]; then
      printf "Active task branch kept: %s (integration target: dev).\n" "$branch"
      exit 0
    fi
    printf "megai dev: refusing to leave active task branch '%s'\n" "$branch" >&2
    exit 1
    ;;
esac

[ -z "$(git status --porcelain --untracked-files=all)" ] || {
  printf "megai dev: '%s' is dirty; commit or stash before switching to dev\n" "$branch" >&2
  exit 1
}

if ! git show-ref --verify --quiet refs/heads/dev; then
  if git show-ref --verify --quiet refs/remotes/origin/dev; then
    git branch --track dev origin/dev >/dev/null
  elif git show-ref --verify --quiet "refs/heads/$base_branch"; then
    git branch dev "$base_branch"
  else
    git branch dev "origin/$base_branch"
  fi
fi

git switch -q dev
git config branch.dev.gh-merge-base "$base_branch"
printf "Development branch ready: %s (dev -> PR base %s).\n" "$root" "$base_branch"
