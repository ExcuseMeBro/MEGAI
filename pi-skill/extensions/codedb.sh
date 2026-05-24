#!/usr/bin/env bash
# megai-codedb — thin wrapper around the codedb CLI
set -euo pipefail

if ! command -v codedb >/dev/null 2>&1; then
  echo "codedb binary not found. Run: megai install" >&2
  exit 1
fi

usage() {
  cat <<EOF
megai-codedb <sub> [args]

  tree [path]       File tree
  search <pat>      Full-text search
  symbol <name>     Locate symbol
  outline <file>    Symbols in file
  find <name>       Find by name
  index [path]      Build index (run once per repo)
EOF
}

case "${1:-help}" in
  tree)     shift; codedb tree    "${1:-.}" ;;
  search)   shift; codedb search  "$@" ;;
  symbol)   shift; codedb symbol  "$@" ;;
  outline)  shift; codedb outline "$@" ;;
  find)     shift; codedb find    "$@" ;;
  index)    shift; codedb index   "${1:-.}" ;;
  help|-h|--help|"") usage ;;
  *) usage; exit 1 ;;
esac
