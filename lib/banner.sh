#!/usr/bin/env bash
# MEGAI banner — printed on install start + first project activation.

if [ -t 1 ]; then
  BNR_FG=$'\033[97m'; BNR_DIM=$'\033[2;37m'; BNR_OFF=$'\033[0m'
else
  BNR_FG=""; BNR_DIM=""; BNR_OFF=""
fi

megai_banner() {
  printf '%s' "$BNR_FG"
  cat <<'EOF'

███╗   ███╗███████╗ ██████╗  █████╗ ██╗
████╗ ████║██╔════╝██╔════╝ ██╔══██╗██║
██╔████╔██║█████╗  ██║  ███╗███████║██║
██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║██║
██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║██║
╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝
EOF
  printf '%s' "$BNR_OFF"
  printf '%s   THE ZERO-CONFIG AI AGENT STACK%s\n\n' "$BNR_DIM" "$BNR_OFF"
}

# tiny variant for `megai` project bootstrap (less vertical space)
megai_banner_mini() {
  printf '%s' "$BNR_FG"
  cat <<'EOF'

  ▄▄   ▄▄  ▄▄▄▄▄  ▄▄▄   ▄▄▄  ▄▄
  ███▄███ ██▀▀▀ ██   ▄ ██▀██ ██
  ██▀█▀██ ████  ██ ▀██ █████ ██
  ██   ██ ██▄▄▄ ▀████ ██   █ ██
EOF
  printf '%s   THE ZERO-CONFIG AI AGENT STACK%s\n\n' "$BNR_DIM" "$BNR_OFF"
}
