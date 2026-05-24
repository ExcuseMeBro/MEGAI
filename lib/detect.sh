#!/usr/bin/env bash
# OS + runtime detection
# Exports: MEGAI_OS, MEGAI_ARCH, MEGAI_PKG, MEGAI_HAS_NODE, MEGAI_HAS_PY, MEGAI_HAS_BREW

detect_os() {
  case "$(uname -s)" in
    Darwin) MEGAI_OS="darwin" ;;
    Linux)  MEGAI_OS="linux"  ;;
    *)      MEGAI_OS="unsupported" ;;
  esac
  case "$(uname -m)" in
    x86_64|amd64)  MEGAI_ARCH="x86_64" ;;
    arm64|aarch64) MEGAI_ARCH="arm64"  ;;
    *)             MEGAI_ARCH="unknown" ;;
  esac
  export MEGAI_OS MEGAI_ARCH
}

detect_runtimes() {
  command -v node    >/dev/null 2>&1 && MEGAI_HAS_NODE=1 || MEGAI_HAS_NODE=0
  command -v python3 >/dev/null 2>&1 && MEGAI_HAS_PY=1   || MEGAI_HAS_PY=0
  command -v pipx    >/dev/null 2>&1 && MEGAI_HAS_PIPX=1 || MEGAI_HAS_PIPX=0
  command -v brew    >/dev/null 2>&1 && MEGAI_HAS_BREW=1 || MEGAI_HAS_BREW=0
  command -v jq      >/dev/null 2>&1 && MEGAI_HAS_JQ=1   || MEGAI_HAS_JQ=0
  command -v curl    >/dev/null 2>&1 && MEGAI_HAS_CURL=1 || MEGAI_HAS_CURL=0
  command -v npm     >/dev/null 2>&1 && MEGAI_HAS_NPM=1  || MEGAI_HAS_NPM=0
  export MEGAI_HAS_NODE MEGAI_HAS_PY MEGAI_HAS_PIPX MEGAI_HAS_BREW MEGAI_HAS_JQ MEGAI_HAS_CURL MEGAI_HAS_NPM
}

require_or_install_node() {
  if [ "$MEGAI_HAS_NODE" = "1" ] && [ "$MEGAI_HAS_NPM" = "1" ]; then return 0; fi
  warn "node/npm yo'q — fnm orqali LTS o'rnataman"
  if [ "$MEGAI_HAS_BREW" = "1" ]; then
    brew install fnm
  else
    curl -fsSL https://fnm.vercel.app/install | bash -s -- --skip-shell
    # shellcheck disable=SC1090
    export PATH="$HOME/.local/share/fnm:$PATH"
    eval "$(fnm env 2>/dev/null || true)"
  fi
  fnm install --lts || die "fnm failed"
  fnm default lts-latest || true
  hash -r
  detect_runtimes
}

require_or_install_python() {
  if [ "$MEGAI_HAS_PY" = "1" ]; then return 0; fi
  warn "python3 yo'q"
  if [ "$MEGAI_HAS_BREW" = "1" ]; then brew install python; fi
  detect_runtimes
}

require_or_install_pipx() {
  if [ "$MEGAI_HAS_PIPX" = "1" ]; then return 0; fi
  warn "pipx yo'q — python -m pip orqali o'rnataman"
  python3 -m pip install --user pipx >/dev/null 2>&1 || true
  python3 -m pipx ensurepath >/dev/null 2>&1 || true
  export PATH="$HOME/.local/bin:$PATH"
  detect_runtimes
}

require_or_install_jq() {
  if [ "$MEGAI_HAS_JQ" = "1" ]; then return 0; fi
  warn "jq yo'q"
  if [ "$MEGAI_HAS_BREW" = "1" ]; then brew install jq
  elif command -v apt-get >/dev/null 2>&1; then sudo apt-get update -qq && sudo apt-get install -y jq
  else die "jq required — manual o'rnating"; fi
  detect_runtimes
}

find_free_port() {
  local p="$1"
  while lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; do
    p=$((p+1))
  done
  echo "$p"
}
